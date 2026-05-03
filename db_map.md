### MAPPA DEL DATABASE
    1. Tabella 'animals':
       - Colonne: card_id (INT), name (STR), latin_name (STR), cost (INT), types (JSON), continents (JSON), enclosure (JSON), requirements (JSON), abilities (JSON), bonuses (JSON)
       - Nota: 'continents' e 'types' sono liste JSON. Esempio query: `SELECT * FROM animals WHERE continents::jsonb ? 'Europe'`
    
    2. Tabella 'sponsors':
       - Colonne: card_id (INT), name (STR), sponsor_strength (FLOAT), requirements (JSON), icons_gained (JSON), instant_bonus, continuing_bonus, end_game_bonus
    
    3. Tabella 'conservation_projects':
       - Colonne: card_id (INT), name (STR), activity_required, size_required (JSON), conservation_points (JSON), requirements_text
    
    4. Tabella 'final_scoring':
       - Colonne: card_id (INT), name (STR), required_tiers (JSON), points_tiers (JSON), additional_details
    
    ### REGOLE DI TRADUZIONE E RICERCA
    - Il database è in INGLESE. Se l'utente chiede in Italiano, traduci i termini tecnici prima di fare la query.
    - Esempi di traduzione:
      * Europa -> 'Europe', Asia -> 'Asia', Africa -> 'Africa', Australia -> 'Australia', Americhe -> 'Americas'
      * Rettile -> 'Reptile', Uccello -> 'Bird', Mammifero -> 'Mammal', Primate -> 'Primate', Animale Petrarso -> 'Petting Zoo Animal'
    - Per i nomi delle carte, usa sempre `ILIKE %termine%` per essere resiliente a errori di battitura.