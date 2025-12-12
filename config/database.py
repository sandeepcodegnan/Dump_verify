"""Database configuration and connection."""
import os
from pymongo import MongoClient
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@st.cache_resource
def get_database():
    """Get MongoDB database connection."""
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "qbank_system_db")
    client = MongoClient(mongo_uri)
    return client[db_name]

def get_collection(collection_name):
    """Get specific collection."""
    db = get_database()
    return db[collection_name]