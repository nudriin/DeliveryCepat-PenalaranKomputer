def astar(graph, start, end, heuristic=lambda x, y: 1):
    import heapq
    queue = [(0, 0, start, [])]
    visited = set()
    while queue:
        (f, cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        path = path + [node]
        if node == end:
            return path
        for neighbor in graph[node]:
            if neighbor not in visited:
                weight = graph[node][neighbor].get("weight", 1)
                g = cost + weight
                h = heuristic(neighbor, end)
                heapq.heappush(queue, (g + h, g, neighbor, path))
    return []