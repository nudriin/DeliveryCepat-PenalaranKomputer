def apply_dynamic_speed(graph, hour):
    for u, v, data in graph.edges(data=True):
        base_speed = data.get("speed", 40)
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            data["speed"] = base_speed * 0.6
        else:
            data["speed"] = base_speed
        distance = data.get("distance", 1)
        data["weight"] = distance / data["speed"]
    return graph