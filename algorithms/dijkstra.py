def dijkstra(graph, start, end):
    import heapq
    queue = [(0, start, [])]
    visited = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        path = path + [node]
        if node == end:
            return path
        for neighbor in graph[node]:
            if neighbor not in visited:
                weight = graph[node][neighbor].get("weight", 1)
                heapq.heappush(queue, (cost + weight, neighbor, path))
    return []