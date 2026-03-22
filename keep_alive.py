import os
from supabase import create_client

def supabase_heartbeat():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Utiliser la Service Role Key pour l'écriture
    
    if not url or not key:
        print("Erreur : Variables d'environnement manquantes.")
        return

    supabase = create_client(url, key)
    
    # Insertion d'une ligne pour simuler une activité d'écriture
    data, count = supabase.table("heartbeat").insert({"status": "cron_active"}).execute()
    
    if data:
        print(f"Succès : Heartbeat enregistré à {data[1][0]['last_check']}")
    else:
        print("Échec de l'insertion.")

if __name__ == "__main__":
    supabase_heartbeat()
