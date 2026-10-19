""""Similar products" recommenders.

`Recommender` is an abstract base class: it defines what every recommender must
do. Two implementations follow, and the app can swap one for the other without
changing any route code (polymorphism).
"""

from abc import ABC, abstractmethod

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Recommender(ABC):
    @abstractmethod
    def fit(self, products):
        """Learn from the full product catalogue."""

    @abstractmethod
    def similar(self, product_id, k=4):
        """Return up to k product ids most similar to product_id (never itself)."""


class CategoryRecommender(Recommender):
    """Baseline: other products in the same category, highest rated first."""

    def fit(self, products):
        self._by_id = {p.id: p for p in products}
        return self

    def similar(self, product_id, k=4):
        target = self._by_id.get(product_id)
        if target is None:
            return []
        same_category = [p for p in self._by_id.values()
                         if p.category == target.category and p.id != product_id]
        same_category.sort(key=lambda p: (-p.rating, p.id))
        return [p.id for p in same_category[:k]]


class TfidfRecommender(Recommender):
    """Content-based: TF-IDF text similarity plus a same-category bonus.

    TF-IDF turns each product's text into numbers, giving more weight to words
    that are rare across the catalogue (like "rattan") than common ones.
    Cosine similarity then scores how close two products' vectors point.
    """

    def __init__(self, category_boost=0.5):
        # Text alone can match a sofa to a bookshelf of the same colour, so
        # products in the same category get a fixed bonus on top of text similarity.
        self.category_boost = category_boost
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))

    def fit(self, products):
        self._ids = [p.id for p in products]
        self._categories = [p.category for p in products]
        self._index = {pid: i for i, pid in enumerate(self._ids)}
        matrix = self._vectorizer.fit_transform(p.search_text() for p in products)
        # Pre-compute every pair once (fine for a few hundred products).
        self._scores = cosine_similarity(matrix)
        return self

    def similar(self, product_id, k=4):
        row = self._index.get(product_id)
        if row is None:
            return []
        category = self._categories[row]
        scores = [score + (self.category_boost if self._categories[i] == category else 0.0)
                  for i, score in enumerate(self._scores[row])]
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], self._ids[i]))
        return [self._ids[i] for i in ranked if i != row][:k]
