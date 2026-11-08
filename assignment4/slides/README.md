# Lecture slides relevant to Assignment 4

Copied from the course folder (`../../../` and `../../../Midterm/`).
Page numbers are **PDF pages** (the decks contain animation builds, so they
differ from the slide numbers printed on each slide).

| Deck | Pages | Why it matters for A4 |
|---|---|---|
| `9-topologies.pdf` | whole deck, especially below | **Main reference.** |
| | 5–9 | Graph measures: degree, distance, diameter, expansion |
| | ~10 (slide 8) | Degree / diameter / cut tradeoff table |
| | ~48–53 | De Bruijn graphs: fixed out-degree, log-diameter, port-count tradeoff (Part 1 candidate construction) |
| | ~61 | Expanders: no narrow region |
| | 100–104 | Feasible flow (capacity + conservation), max-flow/min-cut |
| | 105 | Traffic matrix definition |
| | 107–109 | **Maximum concurrent flow**: path-based LP (`max θ`, capacity, demand constraints) + directed-ring example |
| | 111 | Min-cost flow (flow × hops = capacity used) |
| | 112–116 | Bisection bandwidth, comparison metrics, takeaways ("cut ratios bound concurrent throughput") |
| `12-collective-communication-part-2.pdf` | 31–35 | Relation of collective cost to concurrent flow θ(M, G): "fraction of the traffic matrix that can be routed simultaneously" |
| `13-collective-communication-part-3.pdf` | 23–27, 29 | MoE all-to-all: non-uniform demand matrix; optimal schedule = max concurrent flow solution; reconfigurable-topology reading ("To Reconfigure or Not to Reconfigure") |
| `1-Introduction-Network-Latencies.pdf` | 34–37, 51 | Optical circuit switches / reconfigurable direct-connect topologies — motivation for Part 2's topology that adapts to the traffic matrix |
