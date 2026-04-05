from __future__ import annotations

from dataclasses import dataclass


UNKNOWN = "unknown"
WIN = "win"
LOSS = "loss"


@dataclass(frozen=True)
class SolverMove:
    move_code: int | None
    kind: str
    target: int | None = None


@dataclass(frozen=True)
class SolverNodeResult:
    outcome: str | None
    distance: int | None
    best_move_code: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "distance": self.distance,
            "best_move_code": self.best_move_code,
        }


@dataclass(frozen=True)
class ComponentStats:
    component_id: int
    size: int
    internal_edge_count: int
    outgoing_component_count: int
    frontier_edge_count: int
    terminal_win_edge_count: int
    terminal_loss_edge_count: int
    resolved_win_count: int
    resolved_loss_count: int
    unresolved_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "size": self.size,
            "internal_edge_count": self.internal_edge_count,
            "outgoing_component_count": self.outgoing_component_count,
            "frontier_edge_count": self.frontier_edge_count,
            "terminal_win_edge_count": self.terminal_win_edge_count,
            "terminal_loss_edge_count": self.terminal_loss_edge_count,
            "resolved_win_count": self.resolved_win_count,
            "resolved_loss_count": self.resolved_loss_count,
            "unresolved_count": self.unresolved_count,
        }


@dataclass(frozen=True)
class SccSolveResult:
    node_results: list[SolverNodeResult]
    component_ids: list[int]
    components: list[list[int]]
    component_stats: list[ComponentStats]

    def to_dict(self) -> dict[str, object]:
        return {
            "node_results": [record.to_dict() for record in self.node_results],
            "component_ids": self.component_ids,
            "components": self.components,
            "component_stats": [record.to_dict() for record in self.component_stats],
        }


def compute_sccs(node_count: int, edges_by_node: list[list[int]]) -> tuple[list[int], list[list[int]]]:
    index = 0
    stack: list[int] = []
    on_stack = [False] * node_count
    indices = [-1] * node_count
    lowlinks = [0] * node_count
    component_ids = [-1] * node_count
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack[node] = True

        for target in edges_by_node[node]:
            if indices[target] == -1:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif on_stack[target]:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                member = stack.pop()
                on_stack[member] = False
                component_ids[member] = len(components)
                component.append(member)
                if member == node:
                    break
            component.sort()
            components.append(component)

    for node in range(node_count):
        if indices[node] == -1:
            strongconnect(node)

    return component_ids, components


def solve_via_scc(moves_by_node: list[list[SolverMove]]) -> SccSolveResult:
    node_count = len(moves_by_node)
    graph_edges = [
        [move.target for move in moves if move.kind == "node" and move.target is not None]
        for moves in moves_by_node
    ]
    component_ids, components = compute_sccs(node_count, graph_edges)

    component_edges: list[set[int]] = [set() for _ in components]
    indegree = [0] * len(components)
    for node, edges in enumerate(graph_edges):
        source_component = component_ids[node]
        for target in edges:
            target_component = component_ids[target]
            if source_component != target_component and target_component not in component_edges[source_component]:
                component_edges[source_component].add(target_component)
                indegree[target_component] += 1

    topo: list[int] = []
    queue = [component_id for component_id, value in enumerate(indegree) if value == 0]
    while queue:
        component_id = queue.pop()
        topo.append(component_id)
        for target in component_edges[component_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    reverse_topo = list(reversed(topo))

    statuses = [UNKNOWN] * node_count
    distances: list[int | None] = [None] * node_count
    best_moves: list[int | None] = [None] * node_count

    for component_id in reverse_topo:
        component_nodes = components[component_id]
        changed = True
        while changed:
            changed = False
            for node in component_nodes:
                if statuses[node] != UNKNOWN:
                    continue

                moves = moves_by_node[node]
                if not moves:
                    statuses[node] = LOSS
                    distances[node] = 0
                    changed = True
                    continue

                winning_candidates: list[tuple[int, int]] = []
                losing_candidates: list[tuple[int, int]] = []
                unresolved = False

                for move in moves:
                    move_code = move.move_code if move.move_code is not None else 0
                    if move.kind == "win":
                        winning_candidates.append((1, move_code))
                        continue
                    if move.kind == "loss":
                        losing_candidates.append((1, move_code))
                        continue
                    if move.kind == "unknown" or move.target is None:
                        unresolved = True
                        continue

                    successor_status = statuses[move.target]
                    successor_distance = distances[move.target]
                    if successor_status == LOSS and successor_distance is not None:
                        winning_candidates.append((successor_distance + 1, move_code))
                        continue
                    if successor_status == WIN and successor_distance is not None:
                        losing_candidates.append((successor_distance + 1, move_code))
                        continue
                    unresolved = True

                if winning_candidates:
                    best_distance, best_move = min(winning_candidates, key=lambda item: (item[0], item[1]))
                    statuses[node] = WIN
                    distances[node] = best_distance
                    best_moves[node] = best_move
                    changed = True
                elif not unresolved and len(losing_candidates) == len(moves):
                    best_distance, best_move = max(losing_candidates, key=lambda item: (item[0], -item[1]))
                    statuses[node] = LOSS
                    distances[node] = best_distance
                    best_moves[node] = best_move
                    changed = True

    component_stats: list[ComponentStats] = []
    for component_id, component_nodes in enumerate(components):
        outgoing_components = set()
        frontier_edge_count = 0
        terminal_win_edge_count = 0
        terminal_loss_edge_count = 0
        internal_edge_count = 0
        resolved_win_count = 0
        resolved_loss_count = 0
        unresolved_count = 0

        for node in component_nodes:
            if statuses[node] == WIN:
                resolved_win_count += 1
            elif statuses[node] == LOSS:
                resolved_loss_count += 1
            else:
                unresolved_count += 1

            for move in moves_by_node[node]:
                if move.kind == "win":
                    terminal_win_edge_count += 1
                elif move.kind == "loss":
                    terminal_loss_edge_count += 1
                elif move.kind == "unknown" or move.target is None:
                    frontier_edge_count += 1
                else:
                    target_component = component_ids[move.target]
                    if target_component == component_id:
                        internal_edge_count += 1
                    else:
                        outgoing_components.add(target_component)

        component_stats.append(
            ComponentStats(
                component_id=component_id,
                size=len(component_nodes),
                internal_edge_count=internal_edge_count,
                outgoing_component_count=len(outgoing_components),
                frontier_edge_count=frontier_edge_count,
                terminal_win_edge_count=terminal_win_edge_count,
                terminal_loss_edge_count=terminal_loss_edge_count,
                resolved_win_count=resolved_win_count,
                resolved_loss_count=resolved_loss_count,
                unresolved_count=unresolved_count,
            )
        )

    node_results = [
        SolverNodeResult(
            outcome=None if statuses[node] == UNKNOWN else statuses[node],
            distance=None if statuses[node] == UNKNOWN else distances[node],
            best_move_code=best_moves[node],
        )
        for node in range(node_count)
    ]
    return SccSolveResult(
        node_results=node_results,
        component_ids=component_ids,
        components=components,
        component_stats=component_stats,
    )
