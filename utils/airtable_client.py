import os
import requests
import logging
from typing import List, Dict, Any, Optional

class AirtableClient:
    """Client for interacting with Airtable API"""
    
    def __init__(self, pat: str, base_name: str, table_name: str):
        """
        Initialize the Airtable client
        
        Args:
            pat: Personal Access Token for Airtable
            base_name: Name of the Airtable base
            table_name: Name of the table within the base
        """
        self.pat = pat
        self.base_name = base_name
        self.table_name = table_name
        self.base_id = None
        self.table_id = None
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
        
        # Initialize the client
        self._get_base_and_table_ids()
    
    def _get_base_and_table_ids(self) -> None:
        """Get the base ID and table ID from base name and table name"""
        try:
            # Get list of bases
            bases_url = "https://api.airtable.com/v0/meta/bases"
            response = requests.get(bases_url, headers=self.headers)
            response.raise_for_status()
            
            # Find the base with the matching name
            bases = response.json().get("bases", [])
            matching_base = next((base for base in bases if base.get("name") == self.base_name), None)
            
            if not matching_base:
                raise ValueError(f"Base '{self.base_name}' not found")
            
            self.base_id = matching_base.get("id")
            
            # Get list of tables in the base
            tables_url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
            response = requests.get(tables_url, headers=self.headers)
            response.raise_for_status()
            
            # Find the table with the matching name
            tables = response.json().get("tables", [])
            matching_table = next((table for table in tables if table.get("name") == self.table_name), None)
            
            if not matching_table:
                raise ValueError(f"Table '{self.table_name}' not found in base '{self.base_name}'")
            
            self.table_id = matching_table.get("id")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error connecting to Airtable: {str(e)}")
            raise
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        Get all records from the Airtable table
        
        Returns:
            List of records from the table
        """
        try:
            if not self.base_id or not self.table_id:
                self._get_base_and_table_ids()
            
            records_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_id}"
            response = requests.get(records_url, headers=self.headers)
            response.raise_for_status()
            
            return response.json().get("records", [])
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching records from Airtable: {str(e)}")
            return []
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific record by ID
        
        Args:
            record_id: ID of the record to retrieve
            
        Returns:
            Record data or None if not found
        """
        try:
            if not self.base_id or not self.table_id:
                self._get_base_and_table_ids()
            
            record_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_id}/{record_id}"
            response = requests.get(record_url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching record from Airtable: {str(e)}")
            return None
    
    def update_record(self, record_id: str, fields: Dict[str, Any]) -> bool:
        """
        Update a specific record
        
        Args:
            record_id: ID of the record to update
            fields: Dictionary of field names and values to update
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            if not self.base_id or not self.table_id:
                self._get_base_and_table_ids()
            
            record_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_id}/{record_id}"
            data = {"fields": fields}
            
            response = requests.patch(record_url, headers=self.headers, json=data)
            response.raise_for_status()
            
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error updating record in Airtable: {str(e)}")
            return False
