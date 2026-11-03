import urllib.request
import json
import concurrent.futures

BASE = "https://eth.blockscout.com/api/v2/tokens/0x59468516a8259058baD1cA5F8f4BFF190d30E066/instances"
offsets = [None] + list(range(4951, 0, -50))


def fetch_page(offset):
    url = BASE if offset is None else f"{BASE}?unique_token={offset}"
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.loads(r.read().decode("utf-8"))
                out = []
                for item in data.get("items", []):
                    meta = item.get("metadata") or {}
                    attrs = meta.get("attributes") or []
                    out.append({
                        "id": int(item["id"]),
                        "owner": (item.get("owner") or {}).get("hash"),
                        "ens": (item.get("owner") or {}).get("ens_domain_name"),
                        "image": item.get("image_url"),
                        "attributes": {
                            a.get("trait_type"): a.get("value")
                            for a in attrs
                            if isinstance(a, dict)
                        },
                    })
                return out
        except Exception:
            pass
    return []


def main():
    all_tokens = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for res in ex.map(fetch_page, offsets):
            for t in res:
                all_tokens[t["id"]] = t

    print("Total indexed tokens:", len(all_tokens))

    trait_counts = {}
    for t in all_tokens.values():
        for k, v in t["attributes"].items():
            trait_counts[(k, v)] = trait_counts.get((k, v), 0) + 1

    matches = []
    for t in all_tokens.values():
        vals = " | ".join(f"{k}: {v}" for k, v in t["attributes"].items()).lower()
        if ("fannypack" in vals or "fanny pack" in vals) and "cream" in vals:
            if "light blue / dark blue hoodie jacket" in vals or "hoodie jacket" in vals:
                matches.append(t)

    print("Matches found:", len(matches))
    for m in sorted(matches, key=lambda x: x["id"]):
        tid = m["id"]
        owner = m["ens"] or m["owner"]
        img = m["image"]
        # Calculate statistical rarity score (sum of 1 / (count/total))
        score = 0.0
        for k, v in m["attributes"].items():
            cnt = trait_counts.get((k, v), 1)
            score += 5000.0 / cnt
        print(f"\n=== Token #{tid} | Owner: {owner} | Rarity Score: {score:.1f} ===")
        print(f"Image: {img}")
        for k, v in m["attributes"].items():
            cnt = trait_counts.get((k, v), 0)
            pct = (cnt / max(1, len(all_tokens))) * 100
            print(f"  - {k}: {v} ({cnt}/5000 = {pct:.2f}%)")

    with open(r"C:\Users\souls\.gemini\antigravity\scratch\invisible-friends-tracker\if_5000_traits.json", "w") as f:
        json.dump({"tokens": list(all_tokens.values())}, f)


if __name__ == "__main__":
    main()
