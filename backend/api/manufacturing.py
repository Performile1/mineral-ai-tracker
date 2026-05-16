"""
Mineral AI Tracker - Manufacturing API
Version: 6.0
Description: API endpoint for manufacturing company data (insider investments, contacts)
"""

from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings


# ============================================================================
# Pydantic Models
# ============================================================================

class InsiderInvestment(BaseModel):
    """Response model for insider investments"""
    id: str
    manufacturing_company: str
    manufacturing_ticker: str
    manufacturing_sector: str
    invested_asset: str
    invested_ticker: str
    investment_type: str
    investment_amount: float
    investment_date: str
    percentage_owned: float


class ManufacturingContact(BaseModel):
    """Response model for manufacturing contacts"""
    id: str
    manufacturing_company: str
    manufacturing_ticker: str
    manufacturing_sector: str
    target_company: str
    target_ticker: str
    target_type: str
    contact_type: str
    relationship_strength: str
    last_contact_date: str
    notes: str


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        cursor_factory=RealDictCursor
    )


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/manufacturing", tags=["manufacturing"])


@router.get("/insider-investments")
async def get_insider_investments(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get all manufacturing company insider investments
    Used by frontend ManufacturingInsider component
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # In production, query from proper table
            # For now, return placeholder data structure
            cur.execute("""
                SELECT 
                    id, company_name, ticker, sector,
                    invested_asset, invested_ticker, investment_type,
                    investment_amount, investment_date, percentage_owned
                FROM manufacturing_investments
                ORDER BY investment_date DESC
            """)
            
            # If table doesn't exist or no data, return empty
            try:
                investments = cur.fetchall()
            except:
                investments = []
            
            result = []
            for investment in investments:
                result.append({
                    "id": str(investment['id']),
                    "manufacturing_company": investment['company_name'],
                    "manufacturing_ticker": investment['ticker'],
                    "manufacturing_sector": investment['sector'],
                    "invested_asset": investment['invested_asset'],
                    "invested_ticker": investment['invested_ticker'],
                    "investment_type": investment['investment_type'],
                    "investment_amount": float(investment['investment_amount']),
                    "investment_date": investment['investment_date'].isoformat() if investment['investment_date'] else "",
                    "percentage_owned": float(investment['percentage_owned'])
                })
            
            return {"investments": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/contacts")
async def get_manufacturing_contacts(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get all manufacturing company contacts
    Used by frontend ManufacturingContacts component
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # In production, query from proper table
            cur.execute("""
                SELECT 
                    id, manufacturing_company, manufacturing_ticker,
                    manufacturing_sector, target_company, target_ticker,
                    target_type, contact_type, relationship_strength,
                    last_contact_date, notes
                FROM manufacturing_contacts
                ORDER BY last_contact_date DESC
            """)
            
            # If table doesn't exist or no data, return empty
            try:
                contacts = cur.fetchall()
            except:
                contacts = []
            
            result = []
            for contact in contacts:
                result.append({
                    "id": str(contact['id']),
                    "manufacturing_company": contact['manufacturing_company'],
                    "manufacturing_ticker": contact['manufacturing_ticker'],
                    "manufacturing_sector": contact['manufacturing_sector'],
                    "target_company": contact['target_company'],
                    "target_ticker": contact['target_ticker'],
                    "target_type": contact['target_type'],
                    "contact_type": contact['contact_type'],
                    "relationship_strength": contact['relationship_strength'],
                    "last_contact_date": contact['last_contact_date'].isoformat() if contact['last_contact_date'] else "",
                    "notes": contact['notes']
                })
            
            return {"contacts": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/minerals")
async def get_mineral_data(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get mineral trend and deficit data
    Used by frontend MineralHeatmap component
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    commodity, trend, supply_deficit,
                    capital_inflow, price_change_30d
                FROM macro_demand
                ORDER BY trend DESC
            """)
            
            # If table doesn't exist or no data, return empty
            try:
                minerals = cur.fetchall()
            except:
                minerals = []
            
            result = []
            for mineral in minerals:
                result.append({
                    "commodity": mineral['commodity'],
                    "trend": float(mineral['trend'] or 0),
                    "supply_deficit": float(mineral['supply_deficit'] or 0),
                    "capital_inflow": float(mineral['capital_inflow'] or 0),
                    "price_change_30d": float(mineral['price_change_30d'] or 0),
                    "data_sources": ["LME", "Benchmark Mineral Intelligence", "IEA", "SGU"]  # Placeholder
                })
            
            return {"minerals": result, "count": len(result)}
            
    finally:
        conn.close()
