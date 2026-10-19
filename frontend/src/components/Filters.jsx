const SORTS = [
  { value: "relevance", label: "Most relevant" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "rating", label: "Top rated" },
];

export default function Filters({ filters, categories, onChange }) {
  // Every input updates one key of the filters object held by App.
  const update = (key) => (event) => onChange({ ...filters, [key]: event.target.value });

  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()} aria-label="Search and filters">
      <input
        className="search"
        type="search"
        placeholder="Search sofas, oak, scandinavian…"
        value={filters.q}
        onChange={update("q")}
        aria-label="Search products"
      />
      <select value={filters.category} onChange={update("category")} aria-label="Category">
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c.category} value={c.category}>
            {c.category} ({c.product_count})
          </option>
        ))}
      </select>
      <input
        type="number"
        min="0"
        placeholder="Min ₹"
        value={filters.min_price}
        onChange={update("min_price")}
        aria-label="Minimum price"
      />
      <input
        type="number"
        min="0"
        placeholder="Max ₹"
        value={filters.max_price}
        onChange={update("max_price")}
        aria-label="Maximum price"
      />
      <select value={filters.sort} onChange={update("sort")} aria-label="Sort by">
        {SORTS.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </form>
  );
}
