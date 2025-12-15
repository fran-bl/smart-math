# SmartMath Backend

Ovo je FastAPI backend za SmartMath projekt. Backend se spaja na Supabase bazu (Postgres) preko `DATABASE_URL`.

## Struktura
- `app/main.py` – ulazna točka aplikacije
- `app/config.py` – čitanje `.env` postavki
- `app/db.py` – SQLAlchemy engine, session i Base
- `app/models/` – SQLAlchemy modeli (mapiranje tablica iz baze)
- `app/routers/` – FastAPI routeri (endpointi)
- `.env` – lokalne postavke (DATABASE_URL)
- `requirements.txt` – Python dependencije

## Pokretanje
1. Kreiraj virtualno okruženje:
    cd backend
    python -m venv .venv
    source .venv/bin/activate   # Linux/Mac
    .venv\Scripts\activate      # Windows

2. Instaliraj dependencye:
    pip install -r requirements.txt
    
    WARNING: (ovdje pazite da je verzija sckit-learna barem 1.5.2, inace baca gresku:
    pip install scikit-learn==1.5.2)

3. Dodaj .env datoteku:
    DATABASE_URL=postgresql+psycopg://postgres:lozinka@localhost:5432/postgres (priložim točnu negdje privatno)

4. BITNO! Prije pokretanja servera:
    generiraj dataset i treniraj model -
        cd model
        python generate_train_data.py --n 10000
        python train_mlr.py
    vrati se u backend direktorij - 
        cd ..

4. Pokreni server:
    uvicorn app.main:app --reload --port 8000

5. provjeri inijalne endpointove:
    http://127.0.0.1:8000 - da piše "Backend is running!"
    http://127.0.0.1:8000/health - testni endpoint
    http://127.0.0.1:8000/test/count_users - moj testni endpoint trebalo bi vratiti 1 jer zasad imam samo jednog usera dodanog u bazu
    http://127.0.0.1:8000/docs - popis endpointova

## Što dalje
    Dalje možeš pisati endpointove i nastaviti sve u routers. (health ti je samo za check, a test_db ignoriraj to sam ja testirala jel radi dohvaćanje iz baze)
    Što se tiče modela to bi trebalo biti to, nadam se da sam dodala sve iz baze što je potrebno, ako zatreba još nešto viči.
    Koristi get_db() za rad s bazom.