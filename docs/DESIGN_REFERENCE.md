# Design reference adaptation

The supplied ZIP contains seven 16:9 dashboard screenshots of fleet/operations management interfaces. Common patterns observed:

- Deep charcoal/near-black canvas and layered surfaces.
- Left navigation/sidebar on desktop.
- Dense but clearly separated data panels and KPI cards.
- Amber/teal highlights, neutral typography, subtle borders, and consistent alignment.
- Tables/lists for operational records, plus chart/map modules.

NEXORA translates those patterns to personal finance and community rather than copying the source product's logo, fleet content, or brand identity.

## NEXORA tokens

- Dark canvas: `#0B1117`
- Dark surfaces: `#111B24`, `#17232E`
- Main text: `#F3F6F8`
- Secondary text: `#9AA8B4`
- Teal: `#42D6C5`
- Amber: `#F2B35E`
- Income/positive: `#39C98A`
- Expense/risk: `#F16D72`
- Light canvas: `#F4F7F8`
- Light cards: `#FFFFFF`
- Light text: `#15212B`

The responsive web layout uses a sidebar and multi-column panels; mobile uses one-column cards and five-item bottom navigation. The frontend uses system font fallbacks beginning with Inter/Segoe UI/system-ui because external font downloads are not required at runtime. A lightweight original SVG mascot is included as a static asset; a full 3D animated mascot is not yet implemented.
