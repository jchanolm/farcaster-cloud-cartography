# Farcaster Cloud Cartography

_Note: Created as submission to Balaji's [Cloud Cartography Bounty]([url](https://warpcast.com/balajis.eth/0x983ad3e3))._

# Overview
This repo visualizes social networks from Farcaster by allowing users to input FIDs for accounts on Farcaster and observe how the network between those accounts evolves over time. The visualization displays key metrics like edges, adjacency matrices, and shortest-path matrices, all within an interactive web app.

<img width="887" alt="Screenshot 2024-10-07 at 3 34 18 PM" src="https://github.com/user-attachments/assets/70892569-f2bb-42ad-9a80-7ebeb2f60834">
_Sample Subgraph for Balaji, Vitalik, Dan Romero_

## Repo Structure

The app is divided into four components: 
- **src/data_ingestion/fetch_data.py** pulls the network for provided Farcaster accounts, including following, followers, likes, replies, and recasts, from the Farcaster Hub (I use a Neynar-hosted hub). It also captures account metadata, i.e. profile image.
- **src/data_caching/cache_og_users.ipynb** pulls all required network data for Farcaster accounts with FIDs between 1-10,000 (OG Users) as well as accounts followed by at least two OG users. The data is stored in S3 for later retrieval.
- **src/graph_processing/build_graph.py** constructs the subgraph tying the user-provided Farcaster accounts together. First, it checks to see if network data for the selected account is available in S3. If not, it calls `fetch_data.py` to retrieve the data from the Farcaster hub. 
- **src/graph_viz** contains each module for the Graph Vizualation app.

## Deployment

I deployed with Replit. To run locally, (i) clone repo, (ii) populate an `.env` file with the required `.env` variables, (iii) run `python -m src.graph_viz.app`


## Questions
Questions? Reach out to me @ `jchanolm@gmail.com`
