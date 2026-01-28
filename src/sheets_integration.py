"""
📊 GOOGLE SHEETS INTEGRATION
- Lecture des règles TP/SL depuis une sheet
- Logging des signaux générés
- Sync bidirectionnelle

Requires:
pip install gspread google-auth --break-system-packages
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("⚠️ gspread non installé. pip install gspread google-auth")


class GoogleSheetsManager:
    """
    Gestionnaire Google Sheets pour:
    1. Charger les règles TP/SL (alternative au JSON)
    2. Logger tous les signaux générés
    3. Dashboard de suivi
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, 
                 credentials_path: Optional[str] = None,
                 spreadsheet_id: Optional[str] = None):
        """
        Args:
            credentials_path: Chemin vers le fichier credentials JSON
            spreadsheet_id: ID de la spreadsheet Google
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SPREADSHEET_ID")
        
        self.client = None
        self.spreadsheet = None
        
        if GSPREAD_AVAILABLE and self.credentials_path:
            self._init_client()
    
    def _init_client(self):
        """Initialise le client Google"""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            
            if self.spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        except Exception as e:
            print(f"⚠️ Erreur init Google Sheets: {e}")
    
    def load_rules(self, sheet_name: str = "Rules") -> Dict:
        """
        Charge les règles depuis une sheet Google
        
        Format attendu de la sheet:
        | Asset   | TF  | TP1 | TP2 | TP3 | SL  | Unit |
        |---------|-----|-----|-----|-----|-----|------|
        | BTCUSD  | M1  | 0.5 | 1.0 | 1.5 | 0.7 | %    |
        | BTCUSD  | M5  | 1.0 | 2.0 | 3.5 | 1.5 | %    |
        | XAUUSD  | M1  | 0.3 | 0.6 | 1.0 | 0.5 | %    |
        
        Returns:
            Dict compatible avec config/rules.json
        """
        if not self.spreadsheet:
            return self._load_local_rules()
        
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            records = sheet.get_all_records()
            
            rules = {"assets": {}, "timeframes": {"aliases": {}}, "directions": {}}
            
            for row in records:
                asset = row["Asset"].upper()
                tf = row["TF"].upper()
                
                if asset not in rules["assets"]:
                    rules["assets"][asset] = {"aliases": []}
                
                rules["assets"][asset][tf] = {
                    "tp1": float(row["TP1"]),
                    "tp2": float(row["TP2"]),
                    "tp3": float(row["TP3"]),
                    "sl": float(row["SL"]),
                    "unit": row.get("Unit", "%")
                }
            
            # Ajouter les timeframes aliases standards
            rules["timeframes"]["aliases"] = {
                "1": "M1", "1M": "M1", "5": "M5", "5M": "M5",
                "15": "M15", "15M": "M15", "H1": "H1", "1H": "H1",
                "H4": "H4", "4H": "H4"
            }
            
            rules["directions"] = {
                "LONG": ["LONG", "BUY", "L"],
                "SHORT": ["SHORT", "SELL", "S"]
            }
            
            return rules
            
        except Exception as e:
            print(f"⚠️ Erreur chargement rules: {e}")
            return self._load_local_rules()
    
    def _load_local_rules(self) -> Dict:
        """Fallback: charge depuis le JSON local"""
        path = Path(__file__).parent.parent / "config" / "rules.json"
        with open(path, 'r') as f:
            return json.load(f)
    
    def log_signal(self, signal_data: Dict, sheet_name: str = "Signals"):
        """
        Log un signal dans la sheet
        
        Args:
            signal_data: Données du signal
            sheet_name: Nom de la sheet de logging
        """
        if not self.spreadsheet:
            print("⚠️ Google Sheets non connecté - log ignoré")
            return
        
        try:
            # Créer la sheet si elle n'existe pas
            try:
                sheet = self.spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                sheet = self.spreadsheet.add_worksheet(
                    title=sheet_name, 
                    rows=1000, 
                    cols=15
                )
                # Headers
                headers = [
                    "Timestamp", "Direction", "Asset", "Timeframe",
                    "Entry", "TP1", "TP2", "TP3", "SL", 
                    "RR", "Status", "Result"
                ]
                sheet.append_row(headers)
            
            # Ajouter le signal
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                signal_data.get("direction", ""),
                signal_data.get("asset", ""),
                signal_data.get("timeframe", ""),
                signal_data.get("entry", ""),
                signal_data.get("tp1", ""),
                signal_data.get("tp2", ""),
                signal_data.get("tp3", ""),
                signal_data.get("sl", ""),
                signal_data.get("rr_ratio", ""),
                "SENT",  # Status initial
                ""       # Result (à remplir manuellement)
            ]
            sheet.append_row(row)
            
        except Exception as e:
            print(f"⚠️ Erreur log signal: {e}")
    
    def get_stats(self, sheet_name: str = "Signals") -> Dict:
        """Récupère les statistiques des signaux"""
        if not self.spreadsheet:
            return {"error": "Non connecté"}
        
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            records = sheet.get_all_records()
            
            total = len(records)
            wins = len([r for r in records if r.get("Result") == "WIN"])
            losses = len([r for r in records if r.get("Result") == "LOSS"])
            pending = total - wins - losses
            
            return {
                "total_signals": total,
                "wins": wins,
                "losses": losses,
                "pending": pending,
                "win_rate": f"{(wins/total*100):.1f}%" if total > 0 else "N/A"
            }
            
        except Exception as e:
            return {"error": str(e)}


class SheetsSyncManager:
    """
    Synchronisation bidirectionnelle:
    - Sheet → Config local (règles)
    - Local → Sheet (signaux)
    """
    
    def __init__(self, sheets_manager: GoogleSheetsManager):
        self.sheets = sheets_manager
        self.local_config_path = Path(__file__).parent.parent / "config" / "rules.json"
    
    def sync_rules_to_local(self):
        """Synchronise les règles de la sheet vers le JSON local"""
        rules = self.sheets.load_rules()
        
        with open(self.local_config_path, 'w') as f:
            json.dump(rules, f, indent=2)
        
        print(f"✅ Règles synchronisées: {len(rules['assets'])} assets")
    
    def sync_local_to_sheet(self, sheet_name: str = "RulesBackup"):
        """Backup le JSON local vers une sheet"""
        if not self.sheets.spreadsheet:
            return
        
        rules = self.sheets._load_local_rules()
        
        try:
            try:
                sheet = self.sheets.spreadsheet.worksheet(sheet_name)
                sheet.clear()
            except gspread.WorksheetNotFound:
                sheet = self.sheets.spreadsheet.add_worksheet(
                    title=sheet_name, rows=100, cols=10
                )
            
            # Headers
            headers = ["Asset", "TF", "TP1", "TP2", "TP3", "SL", "Unit"]
            sheet.append_row(headers)
            
            # Data
            for asset, asset_data in rules["assets"].items():
                for tf, tf_data in asset_data.items():
                    if tf == "aliases":
                        continue
                    row = [
                        asset, tf,
                        tf_data.get("tp1", ""),
                        tf_data.get("tp2", ""),
                        tf_data.get("tp3", ""),
                        tf_data.get("sl", ""),
                        tf_data.get("unit", "%")
                    ]
                    sheet.append_row(row)
            
            print(f"✅ Backup créé dans sheet '{sheet_name}'")
            
        except Exception as e:
            print(f"⚠️ Erreur backup: {e}")


# === Template pour créer la spreadsheet ===
SPREADSHEET_TEMPLATE = """
📋 STRUCTURE RECOMMANDÉE DE LA SPREADSHEET

=== Sheet 1: "Rules" (Règles TP/SL) ===
| Asset   | TF  | TP1 | TP2 | TP3 | SL  | Unit   |
|---------|-----|-----|-----|-----|-----|--------|
| BTCUSD  | M1  | 0.5 | 1.0 | 1.5 | 0.7 | %      |
| BTCUSD  | M5  | 1.0 | 2.0 | 3.5 | 1.5 | %      |
| XAUUSD  | M1  | 0.3 | 0.6 | 1.0 | 0.5 | %      |
| XAUUSD  | M5  | 0.5 | 1.0 | 1.5 | 0.8 | %      |
| EURUSD  | M5  | 10  | 20  | 30  | 15  | pips   |
| US30    | M5  | 30  | 60  | 100 | 50  | points |

=== Sheet 2: "Signals" (Log des signaux) ===
| Timestamp           | Direction | Asset  | TF | Entry | TP1   | TP2   | TP3   | SL    | RR  | Status | Result |
|---------------------|-----------|--------|----|----- -|-------|-------|-------|-------|-----|--------|--------|
| 2025-01-28 10:30:00 | LONG      | BTCUSD | M5 | 65000 | 65650 | 66300 | 68275 | 64025 | 2.3 | SENT   | WIN    |

=== Sheet 3: "Dashboard" (Stats) ===
Formules recommandées:
- Total signaux: =COUNTA(Signals!A:A)-1
- Wins: =COUNTIF(Signals!L:L,"WIN")
- Win Rate: =Wins/Total*100
"""

# === Tests ===
if __name__ == "__main__":
    print("=" * 60)
    print("📊 GOOGLE SHEETS INTEGRATION")
    print("=" * 60)
    
    if not GSPREAD_AVAILABLE:
        print("\n⚠️ Pour utiliser Google Sheets:")
        print("pip install gspread google-auth --break-system-packages")
        print("\nConfiguration requise:")
        print("1. Créer un projet Google Cloud")
        print("2. Activer Google Sheets API")
        print("3. Créer un Service Account")
        print("4. Télécharger le fichier credentials.json")
        print("5. Partager la spreadsheet avec le service account")
    else:
        print("\n✅ gspread disponible")
        
        # Test sans credentials (mode simulation)
        manager = GoogleSheetsManager()
        rules = manager._load_local_rules()
        print(f"\n📋 Règles locales chargées: {len(rules['assets'])} assets")
    
    print("\n" + SPREADSHEET_TEMPLATE)
