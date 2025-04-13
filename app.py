import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from data.generated_graph import node_list, edge_list
from data.orders import orders
import time
import pandas as pd
import psutil
import plotly.express as px
import plotly.graph_objects as go
import os

class CityGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_positions = {}
        self._build_graph()
        self._calculate_positions()

    def _build_graph(self):
        for node in node_list:
            self.graph.add_node(node['id'], name=node['name'])
        
        for edge in edge_list:
            time_cost = (edge['distance'] / edge['speed']) * (1 + edge['congestion'])
            self.graph.add_edge(
                edge['from'], 
                edge['to'], 
                weight=time_cost,
                distance=edge['distance'],
                label=f"{edge['distance']}km, {edge['speed']}km/h"
            )
            if not edge['oneway']:
                self.graph.add_edge(
                    edge['to'], 
                    edge['from'], 
                    weight=time_cost,
                    distance=edge['distance'],
                    label=f"{edge['distance']}km, {edge['speed']}km/h"
                )

    def _calculate_positions(self):
        pos = nx.spring_layout(self.graph, seed=42)
        self.node_positions = pos

    def get_shortest_path(self, start, end, algorithm):
        if algorithm == "Dijkstra":
            return nx.dijkstra_path(self.graph, start, end, weight='weight')
        elif algorithm == "A*":
            def heuristic(u, v):
                x1, y1 = self.node_positions[u]
                x2, y2 = self.node_positions[v]
                return ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            return nx.astar_path(self.graph, start, end, heuristic=heuristic, weight='weight')

class EnhancedCityGraph(CityGraph):
    def benchmark_order(self, order, algorithm):
        try:
            dest = order['destination']
            start_time = time.time()
            process = psutil.Process()
            mem_before = process.memory_info().rss
            
            path = self.get_shortest_path(0, dest, algorithm)
            
            mem_after = process.memory_info().rss
            end_time = time.time()
            
            distance = sum(self.graph[u][v]['distance'] for u,v in zip(path[:-1], path[1:]))
            time_cost = sum(self.graph[u][v]['weight'] for u,v in zip(path[:-1], path[1:]))
            
            return {
                'algorithm': algorithm,
                'time': end_time - start_time,
                'memory': (mem_after - mem_before),  # KB
                'distance': distance,
                'time_cost': time_cost,
                'path': path,
                'order_id': order['destination']
            }
        except nx.NetworkXNoPath:
            return None

def assign_orders(orders, vehicle_capacity):
    sorted_orders = sorted(orders, key=lambda x: (-x['priority'], x['deadline']))
    vehicles = []
    current_load = []
    total_weight = 0
    
    for order in sorted_orders:
        if total_weight + order['weight'] <= vehicle_capacity:
            current_load.append(order)
            total_weight += order['weight']
        else:
            vehicles.append(current_load)
            current_load = [order]
            total_weight = order['weight']
    
    if current_load:
        vehicles.append(current_load)
    return vehicles

def plot_network(graph, routes=None):
    plt.figure(figsize=(12, 10))
    nx.draw_networkx_nodes(graph.graph, graph.node_positions, node_color='lightblue', node_size=500)
    nx.draw_networkx_edges(graph.graph, graph.node_positions, edge_color='gray', width=1)
    nx.draw_networkx_labels(graph.graph, graph.node_positions, 
                           {n[0]: n[1]['name'] for n in graph.graph.nodes(data=True)})
    
    if routes:
        colors = plt.cm.tab10.colors
        for i, path in enumerate(routes):
            edges = list(zip(path[:-1], path[1:]))
            nx.draw_networkx_edges(graph.graph, graph.node_positions, edgelist=edges,
                                  edge_color=colors[i], width=2, alpha=0.8)
    
    plt.title("Peta Jaringan Logistik")
    plt.axis('off')
    return plt

def main():
    st.title("🚚 DeliveryCepat - Optimasi Rute Pengiriman")
    graph = CityGraph()
    
    with st.sidebar:
        st.header("⚙️ Parameter")
        algorithm = st.selectbox("Algoritma", ["Dijkstra", "A*"])
        vehicle_capacity = st.slider("Kapasitas Kendaraan (ton)", 10, 50, 20)
        num_vehicles = st.slider("Jumlah Kendaraan", 1, 10, 3)
    
    # Assign orders to vehicles
    vehicles = assign_orders(orders, vehicle_capacity)
    
    # Calculate routes
    all_routes = []
    for vehicle in vehicles[:num_vehicles]:
        destinations = [o['destination'] for o in vehicle]
        path = [0]
        for dest in sorted(destinations, 
                          key=lambda x: nx.dijkstra_path_length(graph.graph, 0, x)):
            path += graph.get_shortest_path(path[-1], dest, algorithm)[1:]
        all_routes.append(path)

    # Visualization
    st.subheader("🗺️ Visualisasi Peta & Rute")
    fig = plot_network(graph, all_routes)
    st.pyplot(fig)
    
    # Metrics
    st.subheader("📊 Dashboard Kinerja")
    total_time = sum(
        sum(graph.graph[u][v]['weight'] for u, v in zip(route[:-1], route[1:]))
        for route in all_routes
    )
    total_distance = sum(
        sum(graph.graph[u][v]['distance'] for u, v in zip(route[:-1], route[1:]))
        for route in all_routes
    )
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Waktu Tempuh", f"{total_time:.2f} jam")
    col2.metric("Total Jarak Tempuh", f"{total_distance:.2f} km")
    col3.metric("Kendaraan Digunakan", len(all_routes))
    
    st.subheader("📦 Detail Pengiriman")
    for i, route in enumerate(all_routes, 1):
        locations = [graph.graph.nodes[n]['name'] for n in route]
        st.write(f"**Kendaraan {i}:** {' → '.join(locations)}")

    #Analisis Komparatif Algoritma
    def analyze_algorithms(graph, orders, vehicle_capacity, num_vehicles):
        st.subheader("📊 Analisis Kualitas Algoritma")

        # 1. Benchmark semua order yang valid
        results = []
        for order in orders:
            dijkstra = graph.benchmark_order(order, "Dijkstra")
            astar = graph.benchmark_order(order, "A*")
            if dijkstra and astar:
                results.extend([dijkstra, astar])

        df = pd.DataFrame(results)

        # 2. Visualisasi Metrik Utama
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.box(df, x='algorithm', y='time', 
                            title='Waktu Komputasi per Algoritma')
                st.plotly_chart(fig)

            with col2:
                fig = px.box(df, x='algorithm', y='memory',
                            title='Penggunaan Memori per Algoritma')
                st.plotly_chart(fig)

            # 3. Analisis Kualitas Solusi
            st.markdown("### Kualitas Solusi")
            solution_df = df.groupby('algorithm').agg({
                'distance': 'mean',
                'time_cost': 'mean'
            }).reset_index()

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=solution_df['algorithm'],
                y=solution_df['distance'],
                name='Jarak Rata-rata',
                marker_color='indigo'
            ))
            fig.add_trace(go.Bar(
                x=solution_df['algorithm'],
                y=solution_df['time_cost'],
                name='Waktu Rata-rata',
                marker_color='royalblue'
            ))
            fig.update_layout(barmode='group', title='Perbandingan Kualitas Solusi')
            st.plotly_chart(fig)

            # 4. Analisis Skalabilitas
            st.markdown("### Skalabilitas dengan Node")
            scalability_data = []
            node_counts = [10, 15, 20, 25, 29]

            for n in node_counts:
                valid_nodes = [node for node in graph.graph.nodes if node <= n]
                subgraph = graph.graph.subgraph(valid_nodes)
                target = min(n, max(valid_nodes))

                try:
                    start = time.time()
                    nx.dijkstra_path(subgraph, 0, target)
                    dijkstra_time = time.time() - start
                except:
                    dijkstra_time = None

                try:
                    start = time.time()
                    nx.astar_path(subgraph, 0, target, heuristic=lambda u,v:0)
                    astar_time = time.time() - start
                except:
                    astar_time = None

                scalability_data.append({
                    'nodes': n,
                    'Dijkstra': dijkstra_time,
                    'A*': astar_time
                })

            fig = px.line(pd.DataFrame(scalability_data), x='nodes', y=['Dijkstra', 'A*'],
                         title='Skalabilitas dengan Peningkatan Node')
            st.plotly_chart(fig)

            # 5. Tabel Detail
            st.markdown("### Data Detail Benchmark")
            st.dataframe(df[['algorithm', 'order_id', 'time', 'memory', 'distance', 'time_cost']]
                        .sort_values(['algorithm', 'order_id']))

    # Panggil di main():
    if st.sidebar.checkbox("Tampilkan Analisis Algoritma"):
        enhanced_graph = EnhancedCityGraph()
        analyze_algorithms(enhanced_graph, orders, vehicle_capacity, num_vehicles)

if __name__ == "__main__":
    main()