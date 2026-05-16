### MAPPA DEL DATABASE
    1. Tabella 'animals':
       - Colonne: card_id (INT), name (STR), latin_name (STR), cost (INT), types (JSON), continents (JSON), enclosure (JSON), requirements (JSON), abilities (JSON), bonuses (JSON)
       - Nota: 'continents' e 'types' sono liste JSON.
       - Per filtrare un continente, NON usare `continents::jsonb ? 'Africa'`: trova solo elementi identici e perde valori come `"Africa x2"`.
       - Esempio corretto per includere anche icone multiple come `Africa x2`:
         `SELECT * FROM animals WHERE EXISTS (SELECT 1 FROM jsonb_array_elements_text(continents::jsonb) AS c(value) WHERE c.value ILIKE 'Africa%')`
       - Per filtrare un tipo animale, vale lo stesso principio: `types` contiene anche valori come `"Sea Animal 2"`, quindi usa `jsonb_array_elements_text(types::jsonb)` con `ILIKE 'Sea Animal%'`.
    
    2. Tabella 'sponsors':
       - Colonne: card_id (INT), name (STR), sponsor_strength (FLOAT), requirements (JSON), icons_gained (JSON), instant_bonus, continuing_bonus, end_game_bonus
       - Nota: 'icons_gained' è una lista JSON ma molti valori combinano quantità e più icone, es. `"1 Herbivore + 1 Rock"`, `"2 Rocks"`, `"1 Sea Animal + 1 Science"`. Per cercare sponsor che danno una certa icona usa `jsonb_array_elements_text(icons_gained::jsonb)` con `ILIKE '%Icona%'`, oppure il tool `get_sponsors_by_icon`.
    
    3. Tabella 'conservation_projects':
       - Colonne: card_id (INT), name (STR), activity_required, size_required (JSON), conservation_points (JSON), requirements_text
    
    4. Tabella 'final_scoring':
       - Colonne: card_id (INT), name (STR), required_tiers (JSON), points_tiers (JSON), additional_details

    5. Tabella 'abilities':
       - Colonne: ability_name (STR), normalized_name (STR), effect (STR), expansion (STR)
       - Nota: contiene la descrizione testuale delle abilità degli animali. I tool animali restituiscono anche `ability_details`, cioè le abilità dell'animale arricchite con effect ed expansion quando disponibili.
    
    ### REGOLE DI TRADUZIONE E RICERCA
    - Il database è in INGLESE. Se l'utente chiede in Italiano, traduci i termini tecnici prima di fare la query.
    - Esempi di traduzione:
      * Europa -> 'Europe', Asia -> 'Asia', Africa -> 'Africa', Australia -> 'Australia', Americhe -> 'Americas'
      * Rettile -> 'Reptile', Uccello -> 'Bird', Mammifero -> 'Mammal', Primate -> 'Primate', Animale Petrarso -> 'Petting Zoo Animal'
    - Per i nomi delle carte, usa sempre `ILIKE %termine%` per essere resiliente a errori di battitura.
    - Per domande sugli animali di un continente, preferisci il tool `get_animals_by_continent` oppure la query con `jsonb_array_elements_text(...)` e `ILIKE 'Continente%'`.
    - Per domande sugli animali di un tipo, preferisci il tool `get_animals_by_type`.
    - Per domande sugli sponsor che danno icone, preferisci il tool `get_sponsors_by_icon`.
