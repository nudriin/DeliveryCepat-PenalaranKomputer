# ==== main.py ====
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from algorithms.dijkstra import dijkstra
from algorithms.astar import astar
from features.dynamic_speed import apply_dynamic_speed
from features.multi_vehicle import assign_orders_to_vehicles
from utils.loader import load_graph

st.set_page_config(page_title="DeliveryCepat Optimizer", layout="wide")
st.title("📦 DeliveryCepat - Optimasi Rute Pengiriman")

# Load graph
graph = load_graph("data/city_graph.gpickle")

# Sidebar controls
algo = st.sidebar.selectbox("Pilih Algoritma", ["Dijkstra", "A*"])
hour = st.sidebar.slider("Jam Simulasi", 0, 23, 8)
vehicle_count = st.sidebar.slider("Jumlah Kendaraan", 1, 5, 2)

if st.button("🔍 Jalankan Optimasi"):
    st.subheader("Hasil Optimasi")

    dynamic_graph = apply_dynamic_speed(graph.copy(), hour)

    if algo == "Dijkstra":
        path_func = dijkstra
    else:
        path_func = astar

    routes = assign_orders_to_vehicles(dynamic_graph, vehicle_count, path_func)

    pos = nx.spring_layout(dynamic_graph, seed=42)
    fig, ax = plt.subplots(figsize=(10, 8))

    colors = ["red", "blue", "green", "orange", "purple"]
    for i, route in enumerate(routes):
        path_edges = list(zip(route, route[1:]))
        nx.draw_networkx_nodes(dynamic_graph, pos, ax=ax, node_size=300)
        nx.draw_networkx_labels(dynamic_graph, pos, ax=ax)
        nx.draw_networkx_edges(dynamic_graph, pos, ax=ax, edgelist=path_edges, edge_color=colors[i % len(colors)], width=2)
        st.write(f"🚚 Kendaraan #{i+1}: {route}")

    st.pyplot(fig)