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
import numpy as np

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
            cost = edge['distance'] * (1 + 0.5 * edge['congestion']) * 1000  # Scale to thousands of rupiah
            self.graph.add_edge(
                edge['from'], 
                edge['to'], 
                weight=time_cost,
                distance=edge['distance'],
                cost=cost,  # Added cost attribute
                label=f"{edge['distance']}km, {edge['speed']}km/h"
            )
            if not edge['oneway']:
                self.graph.add_edge(
                    edge['to'], 
                    edge['from'], 
                    weight=time_cost,
                    distance=edge['distance'],
                    cost=cost,  # Added cost attribute
                    label=f"{edge['distance']}km, {edge['speed']}km/h"
                )

    def _calculate_positions(self):
        pos = nx.spring_layout(self.graph, seed=42)
        self.node_positions = pos

    def get_shortest_path(self, start, end, algorithm):
        start_time = time.time()
        process = psutil.Process()
        mem_before = process.memory_info().rss
        
        if algorithm == "Dijkstra":
            path = nx.dijkstra_path(self.graph, start, end, weight='weight')
        elif algorithm == "A*":
            def heuristic(u, v):
                x1, y1 = self.node_positions[u]
                x2, y2 = self.node_positions[v]
                return ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            path = nx.astar_path(self.graph, start, end, heuristic=heuristic, weight='weight')
        
        mem_after = process.memory_info().rss
        end_time = time.time()
        
        metrics = {
            'time': end_time - start_time,
            'memory': (mem_after - mem_before),
            'path': path
        }
        
        return path, metrics

class EnhancedCityGraph(CityGraph):
    def benchmark_order(self, order, algorithm):
        try:
            dest = order['destination']
            
            path, metrics = self.get_shortest_path(0, dest, algorithm)
            
            distance = sum(self.graph[u][v]['distance'] for u,v in zip(path[:-1], path[1:]))
            time_cost = sum(self.graph[u][v]['weight'] for u,v in zip(path[:-1], path[1:]))
            cost = sum(self.graph[u][v]['cost'] for u,v in zip(path[:-1], path[1:]))
            
            return {
                'algorithm': algorithm,
                'time': metrics['time'],
                'memory': metrics['memory'],
                'distance': distance,
                'time_cost': time_cost,
                'cost': cost,  # Added cost metric
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
                                  edge_color=colors[i % len(colors)], width=2, alpha=0.8)
    
    plt.title("Peta Jaringan Logistik")
    plt.axis('off')
    return plt

def analyze_algorithm_performance(graph, orders, algorithm):
    """Analyze performance of a single algorithm"""
    st.subheader(f"📊 Analisis Kinerja Algoritma {algorithm}")
    
    # 1. Benchmark valid orders
    results = []
    with st.spinner(f"Menganalisis kinerja {algorithm}..."):
        for order in orders:
            result = graph.benchmark_order(order, algorithm)
            if result:
                results.append(result)
    
    if not results:
        st.error("Tidak ada data hasil yang valid untuk dianalisis.")
        return
        
    df = pd.DataFrame(results)
    
    # 2. Performance Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Waktu Komputasi Rata-rata", f"{df['time'].mean():.5f} detik")
    with col2:
        st.metric("Memori Rata-rata", f"{df['memory'].mean()/1024:.2f} KB")
    with col3:
        st.metric("Jarak Rata-rata", f"{df['distance'].mean():.2f} km")
    
    # 3. Detailed Charts
    st.subheader("Detail Metrik per Order")
    
    tab1, tab2, tab3 = st.tabs(["Waktu & Memori", "Kualitas Solusi", "Detail Data"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df, x='order_id', y='time', 
                        title=f'Waktu Komputasi ({algorithm})',
                        labels={'order_id': 'ID Order', 'time': 'Waktu (detik)'})
            fig.update_layout(xaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig)
            
        with col2:
            fig = px.bar(df, x='order_id', y='memory', 
                        title=f'Penggunaan Memori ({algorithm})',
                        labels={'order_id': 'ID Order', 'memory': 'Memori (bytes)'})
            fig.update_layout(xaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df, x='order_id', y=['distance', 'time_cost', 'cost'], 
                        title=f'Kualitas Solusi ({algorithm})',
                        labels={'order_id': 'ID Order', 'value': 'Nilai', 
                               'variable': 'Metrik'},
                        barmode='group')
            fig.update_layout(xaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig)
        
        with col2:
            # Radar chart for solution quality comparison
            metrics = ['distance', 'time_cost', 'cost']
            avg_metrics = df[metrics].mean().tolist()
            max_metrics = df[metrics].max().tolist()
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=avg_metrics,
                theta=metrics,
                fill='toself',
                name='Rata-rata'
            ))
            fig.add_trace(go.Scatterpolar(
                r=max_metrics,
                theta=metrics,
                fill='toself',
                name='Maksimum'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                    )),
                showlegend=True,
                title=f"Profil Kualitas Solusi ({algorithm})"
            )
            st.plotly_chart(fig)
    
    with tab3:
        st.dataframe(df[['order_id', 'time', 'memory', 'distance', 'time_cost', 'cost']]
                    .sort_values('order_id'))

def calculate_min_vehicles(orders, vehicle_capacity):
    """Menghitung jumlah minimal kendaraan yang dibutuhkan"""
    total_weight = sum(o['weight'] for o in orders if o['weight'] <= vehicle_capacity)
    
    # Hitung berdasarkan bin packing dengan prioritas
    sorted_orders = sorted(
        [o for o in orders if o['weight'] <= vehicle_capacity],
        key=lambda x: (-x['priority'], x['deadline'])
    )
    
    vehicles = []
    current_load = 0
    
    for order in sorted_orders:
        if current_load + order['weight'] <= vehicle_capacity:
            current_load += order['weight']
        else:
            vehicles.append(1)
            current_load = order['weight']
    
    if current_load > 0:
        vehicles.append(1)
    
    return max(len(vehicles), int(np.ceil(total_weight / vehicle_capacity)))

def assign_orders(orders, vehicle_capacity):
    """Mengembalikan (vehicles, unassigned_orders)"""
    valid_orders = [o for o in orders if o['weight'] <= vehicle_capacity]
    invalid_orders = [{'id': o['id'], 'reason': 'capacity'} for o in orders if o['weight'] > vehicle_capacity]
    
    sorted_orders = sorted(valid_orders, key=lambda x: (-x['priority'], x['deadline']))
    
    vehicles = []
    current_vehicle = []
    current_load = 0
    
    for order in sorted_orders:
        if current_load + order['weight'] <= vehicle_capacity:
            current_vehicle.append(order)
            current_load += order['weight']
        else:
            vehicles.append(current_vehicle)
            current_vehicle = [order]
            current_load = order['weight']
    
    if current_vehicle:
        vehicles.append(current_vehicle)
    
    # Cek jika masih ada order yang belum teralokasi
    assigned_ids = {o['id'] for vehicle in vehicles for o in vehicle}
    unassigned = [{'id': o['id'], 'reason': 'vehicle_limit'} 
                 for o in sorted_orders if o['id'] not in assigned_ids]
    
    return vehicles, invalid_orders + unassigned

def analyze_scalability(graph, algorithm):
    """Analyze scalability of a single algorithm with increasing nodes"""
    st.subheader(f"🔍 Analisis Skalabilitas {algorithm}")
    
    # Prepare data
    node_counts = list(range(5, len(graph.graph.nodes()), 5))
    if node_counts[-1] != len(graph.graph.nodes()):
        node_counts.append(len(graph.graph.nodes()))
    
    scalability_data = []
    
    with st.spinner(f"Menganalisis skalabilitas {algorithm}..."):
        for n in node_counts:
            valid_nodes = [node for node in graph.graph.nodes() if node < n]
            if len(valid_nodes) < 2:  # Need at least 2 nodes
                continue
                
            subgraph = graph.graph.subgraph(valid_nodes)
            target = max(valid_nodes)
            
            try:
                start_time = time.time()
                process = psutil.Process()
                mem_before = process.memory_info().rss
                
                if algorithm == "Dijkstra":
                    nx.dijkstra_path(subgraph, 0, target)
                else:  # A*
                    def heuristic(u, v):
                        x1, y1 = graph.node_positions[u]
                        x2, y2 = graph.node_positions[v]
                        return ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                    nx.astar_path(subgraph, 0, target, heuristic=heuristic)
                
                mem_after = process.memory_info().rss
                end_time = time.time()
                
                scalability_data.append({
                    'nodes': len(valid_nodes),
                    'time': end_time - start_time,
                    'memory': mem_after - mem_before
                })
            except:
                pass
    
    # Display scalability charts
    if scalability_data:
        scalability_df = pd.DataFrame(scalability_data)
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(scalability_df, x='nodes', y='time',
                         markers=True,
                         title=f'Waktu Komputasi vs Jumlah Node ({algorithm})',
                         labels={'nodes': 'Jumlah Node', 'time': 'Waktu (detik)'})
            st.plotly_chart(fig)
        
        with col2:
            fig = px.line(scalability_df, x='nodes', y='memory',
                         markers=True,
                         title=f'Penggunaan Memori vs Jumlah Node ({algorithm})',
                         labels={'nodes': 'Jumlah Node', 'memory': 'Memori (bytes)'})
            st.plotly_chart(fig)
        
        # Show scalability data table
        st.subheader("Data Skalabilitas")
        st.dataframe(scalability_df)
    else:
        st.error("Tidak dapat menganalisis skalabilitas dengan jaringan saat ini.")

def main():
    st.title("🚚 DeliveryCepat - Optimasi Rute Pengiriman")
    
    # Initialize graph
    graph = EnhancedCityGraph()
    
    with st.sidebar:
        st.header("⚙️ Parameter")
        algorithm = st.selectbox("Algoritma", ["Dijkstra", "A*"])
        vehicle_capacity = st.slider(
            "Kapasitas Kendaraan (ton)", 
            min_value=15,  # Batas minimal 15 ton
            max_value=50, 
            value=20
        )
        
        st.header("📈 Analisis")
        show_performance = st.checkbox("Tampilkan Analisis Kinerja")
        show_scalability = st.checkbox("Tampilkan Analisis Skalabilitas")
    
    # Hitung jumlah kendaraan yang dibutuhkan
    min_vehicles = calculate_min_vehicles(orders, vehicle_capacity)
    
    # Assign orders ke kendaraan
    assigned_vehicles, unassigned_orders = assign_orders(orders, vehicle_capacity)
    
    # Tampilkan informasi alokasi
    st.subheader(f"📦 Alokasi Pengiriman (Membutuhkan {min_vehicles} Kendaraan)")
    
    # Tampilkan peringatan untuk order yang tidak teralokasi
    if unassigned_orders:
        st.error(f"⚠️ {len(unassigned_orders)} order tidak dapat diproses:")
        reasons = {
            'capacity': "melebihi kapasitas kendaraan",
            'vehicle_limit': "keterbatasan jumlah kendaraan"
        }
        for order in unassigned_orders:
            st.write(f"- Order {order['id']} ({reasons[order['reason']]})")
    
    # Hitung rute untuk semua kendaraan
    all_routes = []
    total_metrics = {'time': 0, 'memory': 0, 'distance': 0, 'time_cost': 0, 'cost': 0}
    
    for vehicle in assigned_vehicles:
        destinations = [o['destination'] for o in vehicle]
        path = [0]
        vehicle_metrics = {'time': 0, 'memory': 0, 'distance': 0, 'time_cost': 0, 'cost': 0}
        
        for dest in sorted(destinations):
            next_path, metrics = graph.get_shortest_path(path[-1], dest, algorithm)
            path += next_path[1:]
            
            # Akumulasi metrik
            vehicle_metrics['time'] += metrics['time']
            vehicle_metrics['memory'] += metrics['memory']
            vehicle_metrics['distance'] += sum(graph.graph[u][v]['distance'] for u, v in zip(next_path[:-1], next_path[1:]))
            vehicle_metrics['time_cost'] += sum(graph.graph[u][v]['weight'] for u, v in zip(next_path[:-1], next_path[1:]))
            vehicle_metrics['cost'] += sum(graph.graph[u][v]['cost'] for u, v in zip(next_path[:-1], next_path[1:]))
        
        all_routes.append(path)
        
        # Tambahkan ke total metrik
        for key in total_metrics:
            total_metrics[key] += vehicle_metrics[key]
    
    # Visualisasi
    st.subheader("🗺️ Visualisasi Peta & Rute")
    fig = plot_network(graph, all_routes)
    st.pyplot(fig)
    
    # Performance Overview
    st.subheader("📊 Dashboard Kinerja")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Waktu Tempuh", f"{total_metrics['time_cost']:.2f} jam")
    col2.metric("Total Jarak Tempuh", f"{total_metrics['distance']:.2f} km")
    col3.metric("Total Biaya", f"Rp {total_metrics['cost']:,.0f}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Waktu Komputasi", f"{total_metrics['time']:.5f} detik")
    col2.metric("Penggunaan Memori", f"{total_metrics['memory']/1024:.2f} KB")
    col3.metric("Kendaraan Digunakan", len(assigned_vehicles))
    
    # Detail Rute
    st.subheader("📋 Detail Pengiriman")
    for i, route in enumerate(all_routes, 1):
        locations = [graph.graph.nodes[n]['name'] for n in route]
        st.write(f"**Kendaraan {i}:** {' → '.join(locations)}")
    
    # Analisis tambahan
    if show_performance:
        analyze_algorithm_performance(graph, orders, algorithm)
    
    if show_scalability:
        analyze_scalability(graph, algorithm)

if __name__ == "__main__":
    main()