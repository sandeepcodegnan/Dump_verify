"""Advanced pagination component with performance optimization."""
import streamlit as st
import math

class PaginationComponent:
    def __init__(self, total_items, items_per_page=50, key_prefix=""):
        self.total_items = total_items
        self.items_per_page = items_per_page
        self.key_prefix = key_prefix
        self.total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
        
        # Initialize session state
        if f'{key_prefix}_current_page' not in st.session_state:
            st.session_state[f'{key_prefix}_current_page'] = 1
    
    def render(self):
        """Render pagination controls."""
        current_page = st.session_state[f'{self.key_prefix}_current_page']
        
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", key=f"{self.key_prefix}_first", disabled=current_page == 1):
                st.session_state[f'{self.key_prefix}_current_page'] = 1
                st.rerun()
        
        with col2:
            if st.button("⬅️ Prev", key=f"{self.key_prefix}_prev", disabled=current_page == 1):
                st.session_state[f'{self.key_prefix}_current_page'] = max(1, current_page - 1)
                st.rerun()
        
        with col3:
            # Page selector
            new_page = st.selectbox(
                "Page",
                options=list(range(1, self.total_pages + 1)),
                index=current_page - 1,
                key=f"{self.key_prefix}_page_select",
                format_func=lambda x: f"Page {x} of {self.total_pages}"
            )
            
            if new_page != current_page:
                st.session_state[f'{self.key_prefix}_current_page'] = new_page
                st.rerun()
        
        with col4:
            if st.button("➡️ Next", key=f"{self.key_prefix}_next", disabled=current_page == self.total_pages):
                st.session_state[f'{self.key_prefix}_current_page'] = min(self.total_pages, current_page + 1)
                st.rerun()
        
        with col5:
            if st.button("⏭️ Last", key=f"{self.key_prefix}_last", disabled=current_page == self.total_pages):
                st.session_state[f'{self.key_prefix}_current_page'] = self.total_pages
                st.rerun()
        
        # Info display
        start_item = (current_page - 1) * self.items_per_page + 1
        end_item = min(current_page * self.items_per_page, self.total_items)
        
        st.caption(f"Showing {start_item}-{end_item} of {self.total_items} items")
        
        return current_page
    
    def get_current_page(self):
        """Get current page number."""
        return st.session_state.get(f'{self.key_prefix}_current_page', 1)
    
    def get_offset(self):
        """Get offset for database queries."""
        return (self.get_current_page() - 1) * self.items_per_page