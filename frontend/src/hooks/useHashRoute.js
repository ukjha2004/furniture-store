import { useEffect, useState } from "react";

// A tiny router: pages live after the # in the URL, e.g.
//   #/            store
//   #/login       login / sign up
//   #/checkout    checkout (add ?product=5 for Buy Now)
//   #/orders      my orders,  #/orders/<id>  one order
// The part after # never reaches the server, so this works on Vercel with no extra setup.

function parse() {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path, params: Object.fromEntries(new URLSearchParams(query)) };
}

export function navigate(to) {
  window.location.hash = to;
  window.scrollTo(0, 0);
}

export function useHashRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const onChange = () => setRoute(parse());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
