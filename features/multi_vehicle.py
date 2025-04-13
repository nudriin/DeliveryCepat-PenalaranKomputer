from data.orders import orders

def assign_orders_to_vehicles(graph, vehicle_count, path_func):
    depot = 0
    vehicle_routes = [[] for _ in range(vehicle_count)]
    for i, order in enumerate(orders):
        destination = order["destination"]
        vehicle = i % vehicle_count
        route = path_func(graph, depot, destination)
        vehicle_routes[vehicle].append(depot)
        vehicle_routes[vehicle].extend(route[1:])
        depot = destination
    return vehicle_routes