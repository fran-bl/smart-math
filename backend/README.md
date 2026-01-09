# SmartMath Backend

Ovo je FastAPI backend za SmartMath projekt. Backend se spaja na Supabase bazu (Postgres) preko `DATABASE_URL`.

## Struktura
- `app/main.py` – ulazna točka aplikacije
- `app/config.py` – čitanje `.env` postavki
- `app/db.py` – SQLAlchemy engine, session i Base
- `app/models/` – SQLAlchemy modeli (mapiranje tablica iz baze)
- `app/routers/` – FastAPI routeri (endpointi)
- `.env` – lokalne postavke (DATABASE_URL)
- `requirements.txt` – Python dependencies

## Pokretanje
1. Kreiraj virtualno okruženje:
   ```bash
    cd backend
    python -m venv .venv
    source .venv/bin/activate   # Linux/Mac
    .venv\Scripts\activate      # Windows
   ```

2. Instaliraj dependencye:
    pip install -r requirements.txt
    
    WARNING: (ovdje pazite da je verzija sckit-learna barem 1.5.2, inace baca gresku:
    pip install scikit-learn==1.5.2)

3. Dodaj .env datoteku:<br/>
    `DATABASE_URL="postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres"`<br/>
   U slučaju da IPv6 stvara probleme, alternativa je Session pooler:<br/>
    `DATABASE_URL="postgresql+psycopg://postgres.<PROJECT_REF>:<PASSWORD>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"`

4. BITNO! Prije pokretanja servera:
    generiraj dataset i treniraj model -
        cd model
        python generate_train_data.py --balance
        python train_model.py
    vrati se u backend direktorij - 
        cd ..

4. Pokreni server:
    `uvicorn app.main:app --reload --port 8000`

5. Provjeri inicijalne endpointove:<br/>
    http://127.0.0.1:8000 - da piše "Backend is running!"<br/>
    http://127.0.0.1:8000/health - testni endpoint<br/>
    http://127.0.0.1:8000/test/count_users - moj testni endpoint trebalo bi vratiti 1 jer zasad imam samo jednog usera dodanog u bazu<br/>
    http://127.0.0.1:8000/docs - popis endpointova<br/>

## Što dalje
    Dalje možeš pisati endpointove i nastaviti sve u routers. (health ti je samo za check, a test_db ignoriraj to sam ja testirala jel radi dohvaćanje iz baze)
    Što se tiče modela to bi trebalo biti to, nadam se da sam dodala sve iz baze što je potrebno, ako zatreba još nešto viči.
    Koristi get_db() za rad s bazom.