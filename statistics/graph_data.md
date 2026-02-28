# Graph Data Reference — Hackapizza 2.0

This file contains the raw tabular data behind each of the 16 diagrams,
so that AI agents can read and reason about the data without needing to view images.

**Dataset:** 287 recipes, 62 unique ingredients

---

## 01 — Prestige Distribution

### Summary Statistics

| Stat | Value |
|------|-------|
| count | 287.0 |
| mean | 62.77 |
| std | 16.91 |
| min | 23.0 |
| 25% | 50.0 |
| 50% | 62.0 |
| 75% | 75.0 |
| max | 100.0 |

### Histogram Bins (16 bins)

| Bin Range | Count |
|-----------|-------|
| 23.0 – 27.8 | 2 |
| 27.8 – 32.6 | 6 |
| 32.6 – 37.4 | 13 |
| 37.4 – 42.2 | 10 |
| 42.2 – 47.1 | 24 |
| 47.1 – 51.9 | 30 |
| 51.9 – 56.7 | 29 |
| 56.7 – 61.5 | 24 |
| 61.5 – 66.3 | 36 |
| 66.3 – 71.1 | 25 |
| 71.1 – 75.9 | 17 |
| 75.9 – 80.8 | 18 |
| 80.8 – 85.6 | 25 |
| 85.6 – 90.4 | 15 |
| 90.4 – 95.2 | 8 |
| 95.2 – 100.0 | 5 |

## 02 — Preparation Time Distribution

### Summary Statistics

| Stat | Value |
|------|-------|
| count | 287.0 |
| mean | 9.0 |
| std | 3.48 |
| min | 3.0 |
| 25% | 6.0 |
| 50% | 9.0 |
| 75% | 12.0 |
| max | 15.0 |

### Histogram Bins (30 bins)

| Bin Range (s) | Count |
|---------------|-------|
| 3.00 – 3.40 | 10 |
| 3.40 – 3.80 | 10 |
| 3.80 – 4.20 | 9 |
| 4.20 – 4.60 | 10 |
| 4.60 – 5.00 | 9 |
| 5.00 – 5.40 | 10 |
| 5.40 – 5.80 | 9 |
| 5.80 – 6.20 | 10 |
| 6.20 – 6.60 | 9 |
| 6.60 – 7.00 | 10 |
| 7.00 – 7.40 | 9 |
| 7.40 – 7.80 | 10 |
| 7.80 – 8.20 | 9 |
| 8.20 – 8.60 | 10 |
| 8.60 – 9.00 | 9 |
| 9.00 – 9.40 | 10 |
| 9.40 – 9.80 | 10 |
| 9.80 – 10.20 | 9 |
| 10.20 – 10.60 | 10 |
| 10.60 – 11.00 | 9 |
| 11.00 – 11.40 | 10 |
| 11.40 – 11.80 | 9 |
| 11.80 – 12.20 | 10 |
| 12.20 – 12.60 | 9 |
| 12.60 – 13.00 | 10 |
| 13.00 – 13.40 | 9 |
| 13.40 – 13.80 | 10 |
| 13.80 – 14.20 | 9 |
| 14.20 – 14.60 | 10 |
| 14.60 – 15.00 | 10 |

## 03 — Ingredient Count Distribution

| # Ingredients | # Recipes | % of Total |
|---------------|-----------|------------|
| 5 | 75 | 26.1% |
| 6 | 66 | 23.0% |
| 7 | 51 | 17.8% |
| 8 | 41 | 14.3% |
| 9 | 31 | 10.8% |
| 10 | 19 | 6.6% |
| 11 | 4 | 1.4% |

## 04 — Number of Ingredients vs Prestige (Scatter Data)

- **Pearson r** = 0.1704 (p = 3.7928e-03)
- **Spearman ρ** = 0.1719 (p = 3.4813e-03)

### Per-Recipe Data (n_ingredients, prestige)

| Recipe | # Ing | Prestige |
|--------|-------|----------|
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sf | 5 | 100 |
| Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plas | 5 | 95 |
| Sinfonia di Multiverso: La Danza degli Elementi | 5 | 90 |
| Sinfonia Aromatica del Multiverso | 5 | 89 |
| Viaggio Cosmico nel Multiverso | 5 | 89 |
| Piastrella Celestiale di Gnocchi del Crepuscolo con Nebulosa di Riso di Cassandr | 5 | 86 |
| Sinfonia del Multiverso Calante | 5 | 85 |
| Sinfonia Cosmica di Terracotta | 5 | 85 |
| Sinfonia Cosmica di Andromeda | 5 | 85 |
| Sinfonia Temporale delle Profondità Infrasoniche | 5 | 83 |
| Sinfonia Cosmica: il Ritorno dell'Imperatore | 5 | 82 |
| Sinfonia del Multiverso | 5 | 80 |
| Galassia di Sapori: Sinfonia Transdimensionale | 5 | 80 |
| Sinfonia Cosmica di Proteine Interstellari | 5 | 77 |
| Sinfonia Cosmica di Mare e Stelle | 5 | 77 |
| Sinfonia Celestiale di Echi Galattici | 5 | 77 |
| Nebulosa di Fenice con Sinfonia Eterea | 5 | 75 |
| Sinfonia Cosmica: la Vendetta Fantasma | 5 | 73 |
| Portale del Cosmo: Sinfonia di Sapori Multidimensionali | 5 | 72 |
| Galassia di Sapore Quantum | 5 | 72 |
| Sinfonia Celeste di Granuli Arcobaleno e Riso di Cassandra | 5 | 70 |
| Sinfonia dei Ricordi Celesti | 5 | 70 |
| Nebulosa di Dragone all'Essenza di Vuoto | 5 | 69 |
| Armonia Cosmica alla Tavola d'Oro | 5 | 68 |
| Sinfonia Cosmologica | 5 | 68 |
| Viaggio dei Sensi: Bolla Temporale di Aromi Ancestrali | 5 | 67 |
| Sinfonia Cosmica di Aurora | 5 | 66 |
| Galassia in Tavola: Sinfonia dei Sensi | 5 | 65 |
| Sinfonia di Galassie Perdute | 5 | 63 |
| Universo in Fusilli - Variazione Celestiale | 5 | 62 |
| Mycoflora con Polvere di Stelle Sbagliato | 5 | 62 |
| Sinfonia Crepuscolare | 5 | 61 |
| Risotto Cosmico Multiversale | 5 | 60 |
| Interstellar Requiem | 5 | 60 |
| Danza Cosmica al Crepuscolo | 5 | 60 |
| Mandragola e Radici | 5 | 58 |
| Sinfonia del Cosmo e della Leggenda | 5 | 57 |
| Cosmic Harmony | 5 | 57 |
| Cosmos Quantum Fusion | 5 | 55 |
| Cosmic Harmony Risotto | 5 | 55 |
| Sinfonia Galattica Agentica | 5 | 55 |
| Danza Luminosa del Multiverso | 5 | 53 |
| Enigma Celeste | 5 | 52 |
| Nebulosa di Drago Interdimensionale | 5 | 52 |
| Sinfonia del Cosmo | 5 | 51 |
| Portale di Sapori Arcani | 5 | 50 |
| Viaggio Gastronomico tra le Stelle | 5 | 49 |
| Odissea Cosmica di Nettuno | 5 | 49 |
| Cosmic Rhapsody | 5 | 49 |
| Portale delle Stelle | 5 | 49 |
| Sinfonia Quantica Galattica | 5 | 49 |
| Lumière Cosmica | 5 | 49 |
| Nebulosa di Sapori dell'Infinito | 5 | 49 |
| Il Crepuscolo dell’Unicorno | 5 | 47 |
| Echi del Mare Eterno | 5 | 47 |
| Il Risveglio del Multiverso | 5 | 47 |
| Stellar Fusion | 5 | 46 |
| La Balena Sputafuoco | 5 | 45 |
| Rintocchi del Cosmo | 5 | 44 |
| Più Lontano delle Stelle | 5 | 44 |
| Galassia di Sapori | 5 | 44 |
| Galaxia Rinasciata | 5 | 44 |
| Risotto dei Multiversi | 5 | 43 |
| Galassia d'Aromi Perduti | 5 | 42 |
| Astro-Risotto alle Onde Temporali | 5 | 40 |
| Essenze dell'Infinito | 5 | 36 |
| La Voce del Vento | 5 | 35 |
| Rapsodia Quantistica nel Cosmo | 5 | 35 |
| Galaxia Gustativa | 5 | 35 |
| L'Abbraccio del Cosmo | 5 | 35 |
| Dimensioni del Mare Stellato | 5 | 34 |
| Nebulosa di Sapori Quantici | 5 | 34 |
| Cosmologia Terrestre: Viaggio in Otto Dimensioni | 5 | 32 |
| Nebulosa Galattica | 5 | 31 |
| Etereo Crepuscolare | 5 | 28 |
| Più-dimensionale Sinfonia di Sapori: La Carne del Cosmo | 6 | 95 |
| Sinfonia Quantica dell'Oceano Interstellare | 6 | 94 |
| Sinfonia Celeste dell'Equilibrio Temporale | 6 | 92 |
| Sinfonia Celestiale di Gnocchi del Crepuscolo | 6 | 88 |
| Galassia nel Piatto: Sinfonia di Sapori e Dimensioni | 6 | 87 |
| Sinfonia Cosmica all'Alba di Fenice | 6 | 85 |
| Eterea Sinfonia di Gravità con Infusione Temporale | 6 | 84 |
| Sinfonia del Multiverso Nascente | 6 | 84 |
| Sinfonia Cosmica: Versione Data | 6 | 84 |
| Sinfonia Cosmica ma Fatta Bene | 6 | 82 |
| Galassia a Tavola: Sinfonia di Tempeste Cosmiche | 6 | 82 |
| Sinfonia dell'Infinito: Un Viaggio Gnodale tra Terra e Universi | 6 | 80 |
| Sinfonia di Crepuscolo Celestiale | 6 | 79 |
| Sinfonia Interstellare di Fusilli del Vento con Nettare di Sirena | 6 | 79 |
| Armonia Cosmica della Fenice | 6 | 78 |
| Sinfonia Temporale nello Spaghi del Sole | 6 | 77 |
| Risveglio Cosmico: Un Viaggio nel Sapore Quantistico | 6 | 76 |
| Sinfonia Galattica ai Cristalli di Nebulite | 6 | 73 |
| Sinfonia Temporale Galattica | 6 | 73 |
| Cosmic Synchrony: Il Destino di Pulsar | 6 | 72 |
| Galassia di Celestial Delight | 6 | 71 |
| Sinfonia del Cosmo Rigenerante | 6 | 70 |
| Sinfonia Galattica alla Griglia Cangiante | 6 | 70 |
| Sinfonia Galattica di Sapori con Sorpresa di Drago Fiammante | 6 | 68 |
| Sinfonia di Gusti del Multiverso | 6 | 67 |
| Galassia Infinita: Viaggio tra Memorie e Stelle | 6 | 67 |
| Universo Incantato: Sinfonia dei Gusti Cosmogonici | 6 | 67 |
| Eclissi del Drago nell'Abbraccio del Kraken | 6 | 66 |
| Cosmic Symphony di Ghiaccio e Fuoco | 6 | 66 |
| Valzer Cosmico di Asteria | 6 | 65 |
| Sinfonia Cosmica di Terre e Stelle | 6 | 65 |
| Sinfonia Cosmica alla Szechuan | 6 | 63 |
| Portale Interdimensionale di Sapori | 6 | 62 |
| Il Viaggio Cosmico di Marinetti | 6 | 62 |
| Galassia di Cosmo-Delizie | 6 | 61 |
| Serenata del Multiverso | 6 | 60 |
| Galassie Sospese: Un Viaggio di Sapori Cosmogalattici | 6 | 60 |
| Galassia di Sapore Interdimensionale | 6 | 60 |
| Ecosistema Celeste | 6 | 56 |
| Universo in Fluttuazione | 6 | 56 |
| Galassia Sensoriale | 6 | 55 |
| Pioggia di Dimensioni Galattiche | 6 | 55 |
| Sfogliare Galattico di Sogni Temporali | 6 | 54 |
| Aurora del Cosmo | 6 | 53 |
| Galassia di Sogni Cosmogastronomici | 6 | 52 |
| Galassia di Sapori di Aurora | 6 | 52 |
| Piccola Odissea Cosmica | 6 | 52 |
| Galassia di Sapori Sublimi | 6 | 52 |
| Porta Celestiale alle Stelle | 6 | 50 |
| Galassia Risvegliata | 6 | 47 |
| Portale Astrale di Sapori | 6 | 47 |
| Nebulosa Celeste di Terrafirma | 6 | 47 |
| Cosmos Risotto Reale | 6 | 46 |
| Echi del Cosmo | 6 | 45 |
| Pizza Gio | 6 | 44 |
| Pizza Raul | 6 | 44 |
| Pizza Emma | 6 | 43 |
| Luce e Ombra di Nomea Spaziale | 6 | 40 |
| Sfere del Ricordo Astrale | 6 | 39 |
| Entropia Eterna | 6 | 38 |
| Il Risveglio delle Stelle | 6 | 37 |
| Sassi e Sassolini | 6 | 36 |
| Fenice Galattica | 6 | 35 |
| Verso l'Inedito Oltre | 6 | 30 |
| Dimensioni di Sapori Infusi | 6 | 23 |
| Pizza Luca | 6 | 23 |
| Sinfonia Cosmica del Multiverso | 7 | 100 |
| Sinfonia Cosmica di Armonie Terrestri e Celesti | 7 | 90 |
| Plasma Celestiale al Risotto di Kraken nell'Aura del Sole | 7 | 88 |
| Sinfonia Temporale del Drago | 7 | 82 |
| Sinfonia Astrale | 7 | 82 |
| Sinfonia Cosmica di Luminiscenze e Contrasti | 7 | 81 |
| Sinfonia Cosmica di Sapore | 7 | 80 |
| Viaggio Cosmico tra Mare e Stelle | 7 | 78 |
| Risveglio Cosmico | 7 | 77 |
| Sinfonia dell'Universo Morente | 7 | 75 |
| Viaggio Celeste nel Multiverso | 7 | 74 |
| Sinfonia del Multiverso di Gusto | 7 | 74 |
| Falso Risotto dell'Infinito Multiverso | 7 | 71 |
| Ode al Crepuscolo del Multiverso | 7 | 69 |
| Sinfonia di Galassie Riflesse | 7 | 67 |
| Creazione Celestiale: L'Alba del Cosmo | 7 | 66 |
| Eterna Sinfonia del Cosmo | 7 | 66 |
| Galassia Suprema | 7 | 66 |
| La Mucca Che Stordisce l'Universo | 7 | 66 |
| Cosmic Serenade | 7 | 65 |
| Rivelazione del Multiverso | 7 | 65 |
| Evanescenza Cosmica | 7 | 65 |
| Viaggio dei Ricordi Stellari | 7 | 65 |
| Euforia Cosmica | 7 | 64 |
| Sinfonia Cosmica ma Fatta Male | 7 | 64 |
| Crescendo Cosmico | 7 | 64 |
| Cosmic Harmony Infusion | 7 | 64 |
| L'Estasi Cosmica di Nova | 7 | 63 |
| Pioggia Calante dell'Universo | 7 | 62 |
| Galassia di Sapore Quantico | 7 | 62 |
| Nebulose della Fenice su Vento Lunare | 7 | 61 |
| Odissea Temporale | 7 | 60 |
| La Balena incontra la Mandragora | 7 | 60 |
| Galassia Riflessa | 7 | 56 |
| Sogni di Abisso Cosmico | 7 | 56 |
| Galassia di Sapori Eterei | 7 | 56 |
| Sinfonia Multiversale in Otto Movimenti | 7 | 56 |
| Simfonia Celeste di Aurora | 7 | 52 |
| Sinfonia Galattica | 7 | 52 |
| Alternate Realities Risotto | 7 | 50 |
| Galassia Rinascente | 7 | 50 |
| Evanescenza Quantica | 7 | 50 |
| Il Ricordo del Fuoco Celeste | 7 | 49 |
| Galassia Speculare | 7 | 48 |
| Rapsodia dei Ricordi Celesti | 7 | 46 |
| Cosmos in Tavola | 7 | 42 |
| Cosmopastico di Meraviglie Celesti | 7 | 42 |
| Nebulae Di-Cedri Risvegliati | 7 | 37 |
| L'Eternità al Crepuscolo | 7 | 36 |
| Cosmo Sferico di Sogni Rigenerativi | 7 | 34 |
| Eclissi Armonica di Sapori | 7 | 29 |
| Sinfonia Cosmica: La Danza dell'Universo | 8 | 96 |
| Galassie Infiammate: Sinfonia Cosmica in Sei Dimensioni | 8 | 95 |
| Risveglio Cosmico: Una Sinfonia di Sapori Universali | 8 | 92 |
| Sinfonia Cosmica in Otto Movimenti | 8 | 90 |
| Interstellare Risveglio di Kraken | 8 | 90 |
| Sinfonia Celestiale | 8 | 89 |
| Risotto Interdimensionale alla Carne di Drago e Balena Spaziale con Biscotti del | 8 | 88 |
| Sinfonia Cosmica di Sapori | 8 | 81 |
| Sinfonia Celestiale dei Ricordi | 8 | 81 |
| Galassia Commovente di Stellari | 8 | 79 |
| Viaggio Galattico: Sinfonia dei Sensi | 8 | 75 |
| Sinfonia di Cristalli e Rigenerazione | 8 | 75 |
| Sinfonia Quantistica delle Stelle | 8 | 75 |
| Galassia Incantata: Un Viaggio Attraverso l'Infinito | 8 | 74 |
| Universo Cosmico nel Piatto | 8 | 73 |
| Antipasto Stellare dell'Eterna Armonia | 8 | 72 |
| Nebulosa Celestiale di Sogni Quantici | 8 | 71 |
| Odissea Celestiale | 8 | 69 |
| La Sinfonia dell'Universo | 8 | 68 |
| Concordanza Cosmica | 8 | 65 |
| Galassia di Sapore | 8 | 61 |
| Rivisitazione del Kraken sotto Molecole | 8 | 60 |
| Antipasto Celestiale | 8 | 60 |
| Ode Cosmica di Terra e Stelle | 8 | 60 |
| Galassia di Fusilli Sferici alla Risonanza Crononica | 8 | 59 |
| Rinascita Cosmica | 8 | 59 |
| Bistecca Cacofonica dell'Infinito | 8 | 59 |
| La Creazione di Nova | 8 | 58 |
| Tris di Verdure con Xenodonte | 8 | 58 |
| Cosmopolis delle Galassie Perdute | 8 | 55 |
| L'Unicorno piange il Kraken | 8 | 52 |
| Nebulosa di Confini Sfondati | 8 | 50 |
| Il Viaggio Celeste | 8 | 49 |
| Il Simposio degli Infiniti Ricordi | 8 | 48 |
| Il Risveglio della Fenice sull'Arcobaleno d'Oceano | 8 | 47 |
| L'Ascensione Siderale | 8 | 47 |
| Pizza Fra | 8 | 46 |
| Ethereal Temporal Elixir | 8 | 44 |
| Stella Nova | 8 | 40 |
| Panetto di Carne | 8 | 40 |
| Il Banchetto delle Galassie | 8 | 32 |
| Sinfonia Astrale - Risotto Multiversale con Risacca Celeste | 9 | 100 |
| Galassie in Epifania: Risotto Celestiale con Preziosi dell'Universo | 9 | 97 |
| Nebulose Pensanti: Sinfonia del Multiverso | 9 | 90 |
| Nebulosa Celestiale alla Stellaris | 9 | 90 |
| Sinfonia Quantistica dell'Universo | 9 | 87 |
| Sinfonia di Stagioni Stellari | 9 | 85 |
| Sinfonia Cosmica | 9 | 85 |
| Galassia nel Piatto: Sinfonia Universale di Aromi e Sapori | 9 | 83 |
| Delizia Astrale all'Essenza del Multiverso | 9 | 82 |
| Galassia di Sapori Interstellari | 9 | 82 |
| Sinfonia Cosmica: Versione Pizza | 9 | 79 |
| Sinfonia Cosmica della Rinascita | 9 | 78 |
| Melodia del Multiverso Parallelo | 9 | 70 |
| Sinfonia degli Elementi Eterni | 9 | 70 |
| Il Risveglio del Drago Celeste | 9 | 70 |
| Il Rapsodo Celestiale | 9 | 70 |
| Risotto Cosmico alla Draconia | 9 | 68 |
| Galassie alla Spirale di Vento con Sfera di Ghiaccio Eterno | 9 | 64 |
| Fenice sull'Orizzonte degli Eventi | 9 | 63 |
| Universo in Un Boccone | 9 | 62 |
| Galassia Ardente | 9 | 62 |
| Cosmofantasia di Terra e Mare nel Vortice delle Stelle | 9 | 60 |
| Pioggia di Andromeda | 9 | 56 |
| Il Viaggio delle Dimensioni Confluenti | 9 | 55 |
| Il Viaggio dell'Etereo Risveglio | 9 | 55 |
| Galassia di Sapori: Il Viaggio Senza Tempo | 9 | 55 |
| Nebulose a Strati | 9 | 50 |
| Tris di Carne con Pane | 9 | 50 |
| Valzer delle Stelle | 9 | 50 |
| Nebulosa Eterna | 9 | 50 |
| Pizza Baby Simone e Alessandro | 9 | 50 |
| Quadrifonia Cosmica: Sinfonia di Sapori e Dimensioni | 10 | 95 |
| Galassia di Sapore Interstellare | 10 | 94 |
| Sinfonia Temporale al Tocco di Crono | 10 | 85 |
| Sinfonia Cosmica: Il Crescendo delle Stelle | 10 | 84 |
| Pizza Cosmica all'Essenza di Drago con Nebbia Arcobaleno e Funghi Orbitali | 10 | 83 |
| Portale Cosmico del Kraken | 10 | 79 |
| Portale del Cosmo: Sinfonia di Sapori e Tempi | 10 | 75 |
| Galassia di Sapori: L'Eterno Ritorno | 10 | 71 |
| Una Mucca e una Balena nella Singolarità | 10 | 63 |
| Fusione Celeste | 10 | 62 |
| Nebulosa dell'Infinito: Un Viaggio attraverso il Cosmo del Gusto | 10 | 54 |
| Pane e Carne Rivisitato | 10 | 50 |
| Microcosmo in un Boccone | 10 | 50 |
| Cosmos Culinary Symphony | 10 | 50 |
| Portale delle Meraviglie | 10 | 50 |
| Pizza Cri | 10 | 50 |
| Pizza Baby Daniele | 10 | 50 |
| Pizza Baby Lorenzo | 10 | 50 |
| Eclissi Quantica: Viaggio nei Reami del Gusto | 10 | 47 |
| Galassie Riflesse: Sinfonia del Multiverso | 11 | 83 |
| Galassia Aurorale | 11 | 66 |
| Sinfonia Tempolare Galattica | 11 | 64 |
| Nebulare Asteroideo con Crepuscolo di Mucca | 11 | 40 |

## 05 — Mean Prestige by Ingredient Count

|   n_ingredients |   mean |   median |   std |   count |   min |   max |
|----------------:|-------:|---------:|------:|--------:|------:|------:|
|               5 |  59.05 |       57 | 17.68 |      75 |    28 |   100 |
|               6 |  61.59 |       62 | 17.61 |      66 |    23 |    95 |
|               7 |  62.29 |       64 | 14.82 |      51 |    29 |   100 |
|               8 |  65.41 |       61 | 16.83 |      41 |    32 |    96 |
|               9 |  69.94 |       70 | 15.23 |      31 |    50 |   100 |
|              10 |  65.37 |       62 | 16.98 |      19 |    47 |    95 |
|              11 |  63.25 |       65 | 17.69 |       4 |    40 |    83 |

## 06 — Preparation Time vs Prestige

- **Pearson r** = -0.1224 (p = 3.8220e-02)
- **Spearman ρ** = -0.1160 (p = 4.9548e-02)

### Per-Recipe Data (prep_s, prestige)

| Recipe | Prep (s) | Prestige |
|--------|----------|----------|
| Nebulosa Galattica | 3.000 | 31 |
| Sinfonia Cosmica di Proteine Interstellari | 3.042 | 77 |
| L'Estasi Cosmica di Nova | 3.084 | 63 |
| Viaggio Galattico: Sinfonia dei Sensi | 3.126 | 75 |
| Cosmic Synchrony: Il Destino di Pulsar | 3.168 | 72 |
| Il Crepuscolo dell’Unicorno | 3.210 | 47 |
| Galassia di Sapore | 3.252 | 61 |
| Il Risveglio della Fenice sull'Arcobaleno d'Oceano | 3.294 | 47 |
| Il Viaggio Celeste | 3.336 | 49 |
| Luce e Ombra di Nomea Spaziale | 3.378 | 40 |
| La Creazione di Nova | 3.420 | 58 |
| Eterea Sinfonia di Gravità con Infusione Temporale | 3.462 | 84 |
| Universo in Fusilli - Variazione Celestiale | 3.503 | 62 |
| Cosmic Serenade | 3.545 | 65 |
| Ecosistema Celeste | 3.587 | 56 |
| Universo in Un Boccone | 3.629 | 62 |
| Nebulosa Celestiale di Sogni Quantici | 3.671 | 71 |
| Universo Cosmico nel Piatto | 3.713 | 73 |
| Galassia Speculare | 3.755 | 48 |
| Sinfonia del Multiverso Nascente | 3.797 | 84 |
| Antipasto Stellare dell'Eterna Armonia | 3.839 | 72 |
| Essenze dell'Infinito | 3.881 | 36 |
| Etereo Crepuscolare | 3.923 | 28 |
| Sinfonia del Multiverso Calante | 3.965 | 85 |
| Sinfonia Quantica dell'Oceano Interstellare | 4.007 | 94 |
| Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plas | 4.049 | 95 |
| Nebulare Asteroideo con Crepuscolo di Mucca | 4.091 | 40 |
| Sinfonia Temporale del Drago | 4.133 | 82 |
| Il Viaggio delle Dimensioni Confluenti | 4.175 | 55 |
| Echi del Mare Eterno | 4.217 | 47 |
| Odissea Temporale | 4.259 | 60 |
| Rintocchi del Cosmo | 4.301 | 44 |
| Armonia Cosmica alla Tavola d'Oro | 4.343 | 68 |
| Echi del Cosmo | 4.385 | 45 |
| Ethereal Temporal Elixir | 4.427 | 44 |
| Sinfonia Celestiale di Gnocchi del Crepuscolo | 4.469 | 88 |
| Eclissi Armonica di Sapori | 4.510 | 29 |
| Il Viaggio dell'Etereo Risveglio | 4.552 | 55 |
| Sinfonia Cosmica di Mare e Stelle | 4.594 | 77 |
| Pane e Carne Rivisitato | 4.636 | 50 |
| Risotto Cosmico Multiversale | 4.678 | 60 |
| Il Risveglio del Multiverso | 4.720 | 47 |
| Sinfonia del Cosmo e della Leggenda | 4.762 | 57 |
| Cosmos Quantum Fusion | 4.804 | 55 |
| Più-dimensionale Sinfonia di Sapori: La Carne del Cosmo | 4.846 | 95 |
| Plasma Celestiale al Risotto di Kraken nell'Aura del Sole | 4.888 | 88 |
| Risotto Interdimensionale alla Carne di Drago e Balena Spaziale con Biscotti del | 4.930 | 88 |
| Alternate Realities Risotto | 4.972 | 50 |
| Sinfonia Cosmica: Versione Pizza | 5.014 | 79 |
| Galassia di Sapore Interstellare | 5.056 | 94 |
| Sinfonia Cosmica di Sapore | 5.098 | 80 |
| Sinfonia Cosmica di Luminiscenze e Contrasti | 5.140 | 81 |
| Sinfonia Cosmica in Otto Movimenti | 5.182 | 90 |
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sf | 5.224 | 100 |
| Sinfonia Cosmica: Versione Data | 5.266 | 84 |
| Sinfonia Cosmologica | 5.308 | 68 |
| Sinfonia Cosmica di Armonie Terrestri e Celesti | 5.350 | 90 |
| Cosmo Sferico di Sogni Rigenerativi | 5.392 | 34 |
| Sinfonia di Cristalli e Rigenerazione | 5.434 | 75 |
| Stella Nova | 5.476 | 40 |
| Sinfonia del Multiverso | 5.517 | 80 |
| Sinfonia di Multiverso: La Danza degli Elementi | 5.559 | 90 |
| Più Lontano delle Stelle | 5.601 | 44 |
| Sinfonia Cosmica del Multiverso | 5.643 | 100 |
| Viaggio Celeste nel Multiverso | 5.685 | 74 |
| Sinfonia di Gusti del Multiverso | 5.727 | 67 |
| Portale del Cosmo: Sinfonia di Sapori Multidimensionali | 5.769 | 72 |
| Sinfonia Galattica ai Cristalli di Nebulite | 5.811 | 73 |
| Sinfonia Tempolare Galattica | 5.853 | 64 |
| Cosmopolis delle Galassie Perdute | 5.895 | 55 |
| Galassia Risvegliata | 5.937 | 47 |
| Sinfonia Temporale nello Spaghi del Sole | 5.979 | 77 |
| Sinfonia di Crepuscolo Celestiale | 6.021 | 79 |
| Sinfonia di Stagioni Stellari | 6.063 | 85 |
| Viaggio dei Sensi: Bolla Temporale di Aromi Ancestrali | 6.105 | 67 |
| Sfogliare Galattico di Sogni Temporali | 6.147 | 54 |
| Nebulosa di Fenice con Sinfonia Eterea | 6.189 | 75 |
| Sinfonia Temporale al Tocco di Crono | 6.231 | 85 |
| Viaggio Gastronomico tra le Stelle | 6.273 | 49 |
| Sinfonia del Cosmo Rigenerante | 6.315 | 70 |
| Delizia Astrale all'Essenza del Multiverso | 6.357 | 82 |
| Melodia del Multiverso Parallelo | 6.399 | 70 |
| Portale Interdimensionale di Sapori | 6.441 | 62 |
| Ode al Crepuscolo del Multiverso | 6.483 | 69 |
| Sinfonia Interstellare di Fusilli del Vento con Nettare di Sirena | 6.524 | 79 |
| La Voce del Vento | 6.566 | 35 |
| Nebulose a Strati | 6.608 | 50 |
| Sinfonia Aromatica del Multiverso | 6.650 | 89 |
| Serenata del Multiverso | 6.692 | 60 |
| Euforia Cosmica | 6.734 | 64 |
| Galassie Riflesse: Sinfonia del Multiverso | 6.776 | 83 |
| Sinfonia Cosmica di Terracotta | 6.818 | 85 |
| Viaggio Cosmico nel Multiverso | 6.860 | 89 |
| Dimensioni del Mare Stellato | 6.902 | 34 |
| Danza Luminosa del Multiverso | 6.944 | 53 |
| Microcosmo in un Boccone | 6.986 | 50 |
| Nebulose della Fenice su Vento Lunare | 7.028 | 61 |
| Nebulose Pensanti: Sinfonia del Multiverso | 7.070 | 90 |
| Nebulosa Celestiale alla Stellaris | 7.112 | 90 |
| Sinfonia Cosmica ma Fatta Male | 7.154 | 64 |
| Astro-Risotto alle Onde Temporali | 7.196 | 40 |
| Sinfonia Galattica alla Griglia Cangiante | 7.238 | 70 |
| Galassie Infiammate: Sinfonia Cosmica in Sei Dimensioni | 7.280 | 95 |
| Galassie Sospese: Un Viaggio di Sapori Cosmogalattici | 7.322 | 60 |
| Pioggia di Andromeda | 7.364 | 56 |
| Sinfonia Cosmica ma Fatta Bene | 7.406 | 82 |
| Odissea Cosmica di Nettuno | 7.448 | 49 |
| Galassia Commovente di Stellari | 7.490 | 79 |
| Risotto dei Multiversi | 7.531 | 43 |
| Panetto di Carne | 7.573 | 40 |
| Cosmos Risotto Reale | 7.615 | 46 |
| La Balena incontra la Mandragora | 7.657 | 60 |
| Armonia Cosmica della Fenice | 7.699 | 78 |
| Fenice Galattica | 7.741 | 35 |
| Rapsodia Quantistica nel Cosmo | 7.783 | 35 |
| Galassia di Sapore Quantum | 7.825 | 72 |
| Tris di Carne con Pane | 7.867 | 50 |
| Galassia Riflessa | 7.909 | 56 |
| Enigma Celeste | 7.951 | 52 |
| Galassia d'Aromi Perduti | 7.993 | 42 |
| Galassia a Tavola: Sinfonia di Tempeste Cosmiche | 8.035 | 82 |
| Portale Astrale di Sapori | 8.077 | 47 |
| Cosmic Harmony Risotto | 8.119 | 55 |
| Galassia di Celestial Delight | 8.161 | 71 |
| Pioggia Calante dell'Universo | 8.203 | 62 |
| Creazione Celestiale: L'Alba del Cosmo | 8.245 | 66 |
| Cosmic Rhapsody | 8.287 | 49 |
| Rivisitazione del Kraken sotto Molecole | 8.329 | 60 |
| Sinfonia Celestiale | 8.371 | 89 |
| Sinfonia Cosmica di Sapori | 8.413 | 81 |
| Galassia di Sogni Cosmogastronomici | 8.455 | 52 |
| Entropia Eterna | 8.497 | 38 |
| Valzer delle Stelle | 8.538 | 50 |
| Sinfonia di Galassie Riflesse | 8.580 | 67 |
| Valzer Cosmico di Asteria | 8.622 | 65 |
| Galassia Infinita: Viaggio tra Memorie e Stelle | 8.664 | 67 |
| Eterna Sinfonia del Cosmo | 8.706 | 66 |
| Sinfonia Cosmica di Aurora | 8.748 | 66 |
| Galaxia Gustativa | 8.790 | 35 |
| Crescendo Cosmico | 8.832 | 64 |
| Simfonia Celeste di Aurora | 8.874 | 52 |
| Portale del Cosmo: Sinfonia di Sapori e Tempi | 8.916 | 75 |
| Verso l'Inedito Oltre | 8.958 | 30 |
| Sinfonia di Galassie Perdute | 9.000 | 63 |
| Sinfonia degli Elementi Eterni | 9.042 | 70 |
| Galassie in Epifania: Risotto Celestiale con Preziosi dell'Universo | 9.084 | 97 |
| Galassia Suprema | 9.126 | 66 |
| Fusione Celeste | 9.168 | 62 |
| Sinfonia Cosmica di Andromeda | 9.210 | 85 |
| Risveglio Cosmico: Una Sinfonia di Sapori Universali | 9.252 | 92 |
| Galassia Incantata: Un Viaggio Attraverso l'Infinito | 9.294 | 74 |
| Sinfonia Celestiale di Echi Galattici | 9.336 | 77 |
| Porta Celestiale alle Stelle | 9.378 | 50 |
| Sinfonia Celeste dell'Equilibrio Temporale | 9.420 | 92 |
| Il Risveglio delle Stelle | 9.462 | 37 |
| Nebulosa di Drago Interdimensionale | 9.503 | 52 |
| Sinfonia Cosmica: La Danza dell'Universo | 9.545 | 96 |
| Interstellar Requiem | 9.587 | 60 |
| Nebulae Di-Cedri Risvegliati | 9.629 | 37 |
| Nebulosa dell'Infinito: Un Viaggio attraverso il Cosmo del Gusto | 9.671 | 54 |
| Nebulosa Eterna | 9.713 | 50 |
| Risveglio Cosmico | 9.755 | 77 |
| Aurora del Cosmo | 9.797 | 53 |
| Galassia nel Piatto: Sinfonia di Sapori e Dimensioni | 9.839 | 87 |
| Nebulosa Celeste di Terrafirma | 9.881 | 47 |
| Universo in Fluttuazione | 9.923 | 56 |
| Sinfonia Astrale - Risotto Multiversale con Risacca Celeste | 9.965 | 100 |
| Sinfonia Temporale Galattica | 10.007 | 73 |
| Sinfonia del Multiverso di Gusto | 10.049 | 74 |
| Sinfonia Cosmica | 10.091 | 85 |
| Danza Cosmica al Crepuscolo | 10.133 | 60 |
| Sinfonia Astrale | 10.175 | 82 |
| Dimensioni di Sapori Infusi | 10.217 | 23 |
| Cosmos Culinary Symphony | 10.259 | 50 |
| Portale delle Meraviglie | 10.301 | 50 |
| Galassia di Sapori Interstellari | 10.343 | 82 |
| Galassia Aurorale | 10.385 | 66 |
| Galassia di Sapori: L'Eterno Ritorno | 10.427 | 71 |
| Rivelazione del Multiverso | 10.469 | 65 |
| Sinfonia Cosmica della Rinascita | 10.510 | 78 |
| Galassia di Sapori | 10.552 | 44 |
| Stellar Fusion | 10.594 | 46 |
| Portale delle Stelle | 10.636 | 49 |
| Sogni di Abisso Cosmico | 10.678 | 56 |
| Viaggio Cosmico tra Mare e Stelle | 10.720 | 78 |
| Nebulosa di Dragone all'Essenza di Vuoto | 10.762 | 69 |
| Il Viaggio Cosmico di Marinetti | 10.804 | 62 |
| Piastrella Celestiale di Gnocchi del Crepuscolo con Nebulosa di Riso di Cassandr | 10.846 | 86 |
| Sinfonia Celeste di Granuli Arcobaleno e Riso di Cassandra | 10.888 | 70 |
| Cosmos in Tavola | 10.930 | 42 |
| Eclissi del Drago nell'Abbraccio del Kraken | 10.972 | 66 |
| Sinfonia Quantica Galattica | 11.014 | 49 |
| Sinfonia Galattica Agentica | 11.056 | 55 |
| Galassia di Sapori Eterei | 11.098 | 56 |
| Il Risveglio del Drago Celeste | 11.140 | 70 |
| L'Abbraccio del Cosmo | 11.182 | 35 |
| Cosmic Harmony Infusion | 11.224 | 64 |
| Concordanza Cosmica | 11.266 | 65 |
| Universo Incantato: Sinfonia dei Gusti Cosmogonici | 11.308 | 67 |
| Eclissi Quantica: Viaggio nei Reami del Gusto | 11.350 | 47 |
| Sinfonia Multiversale in Otto Movimenti | 11.392 | 56 |
| La Sinfonia dell'Universo | 11.434 | 68 |
| Sinfonia dell'Universo Morente | 11.476 | 75 |
| Sinfonia Cosmica: la Vendetta Fantasma | 11.517 | 73 |
| Antipasto Celestiale | 11.559 | 60 |
| Sinfonia Cosmica: il Ritorno dell'Imperatore | 11.601 | 82 |
| Evanescenza Cosmica | 11.643 | 65 |
| Galassia nel Piatto: Sinfonia Universale di Aromi e Sapori | 11.685 | 83 |
| Sinfonia Galattica di Sapori con Sorpresa di Drago Fiammante | 11.727 | 68 |
| Galassia di Sapori di Aurora | 11.769 | 52 |
| Galassia di Sapore Interdimensionale | 11.811 | 60 |
| Galassia di Sapori: Sinfonia Transdimensionale | 11.853 | 80 |
| Il Ricordo del Fuoco Celeste | 11.895 | 49 |
| Sinfonia dei Ricordi Celesti | 11.937 | 70 |
| Sinfonia del Cosmo | 11.979 | 51 |
| Rapsodia dei Ricordi Celesti | 12.021 | 46 |
| Il Simposio degli Infiniti Ricordi | 12.063 | 48 |
| Viaggio dei Ricordi Stellari | 12.105 | 65 |
| Sinfonia Crepuscolare | 12.147 | 61 |
| Sinfonia Celestiale dei Ricordi | 12.189 | 81 |
| Sfere del Ricordo Astrale | 12.231 | 39 |
| Pizza Fra | 12.273 | 46 |
| Pizza Gio | 12.315 | 44 |
| Pizza Emma | 12.357 | 43 |
| Pizza Luca | 12.399 | 23 |
| Pizza Raul | 12.441 | 44 |
| Pizza Cri | 12.483 | 50 |
| Pizza Baby Daniele | 12.524 | 50 |
| Pizza Baby Lorenzo | 12.566 | 50 |
| Pizza Baby Simone e Alessandro | 12.608 | 50 |
| Quadrifonia Cosmica: Sinfonia di Sapori e Dimensioni | 12.650 | 95 |
| Sinfonia Cosmica di Terre e Stelle | 12.692 | 65 |
| Lumière Cosmica | 12.734 | 49 |
| Risveglio Cosmico: Un Viaggio nel Sapore Quantistico | 12.776 | 76 |
| L'Ascensione Siderale | 12.818 | 47 |
| Portale di Sapori Arcani | 12.860 | 50 |
| Fenice sull'Orizzonte degli Eventi | 12.902 | 63 |
| Portale Cosmico del Kraken | 12.944 | 79 |
| Una Mucca e una Balena nella Singolarità | 12.986 | 63 |
| Risotto Cosmico alla Draconia | 13.028 | 68 |
| Galassia di Fusilli Sferici alla Risonanza Crononica | 13.070 | 59 |
| Galassia Rinascente | 13.112 | 50 |
| Mandragola e Radici | 13.154 | 58 |
| Galaxia Rinasciata | 13.196 | 44 |
| Cosmic Harmony | 13.238 | 57 |
| Nebulosa di Sapori Quantici | 13.280 | 34 |
| Galassia in Tavola: Sinfonia dei Sensi | 13.322 | 65 |
| Galassie alla Spirale di Vento con Sfera di Ghiaccio Eterno | 13.364 | 64 |
| La Mucca Che Stordisce l'Universo | 13.406 | 66 |
| Piccola Odissea Cosmica | 13.448 | 52 |
| L'Unicorno piange il Kraken | 13.490 | 52 |
| L'Eternità al Crepuscolo | 13.531 | 36 |
| La Balena Sputafuoco | 13.573 | 45 |
| Sassi e Sassolini | 13.615 | 36 |
| Galassia Ardente | 13.657 | 62 |
| Galassia di Cosmo-Delizie | 13.699 | 61 |
| Nebulosa di Confini Sfondati | 13.741 | 50 |
| Galassia Sensoriale | 13.783 | 55 |
| Cosmopastico di Meraviglie Celesti | 13.825 | 42 |
| Sinfonia Cosmica all'Alba di Fenice | 13.867 | 85 |
| Sinfonia Cosmica alla Szechuan | 13.909 | 63 |
| Sinfonia Cosmica: Il Crescendo delle Stelle | 13.951 | 84 |
| Cosmofantasia di Terra e Mare nel Vortice delle Stelle | 13.993 | 60 |
| Cosmic Symphony di Ghiaccio e Fuoco | 14.035 | 66 |
| Odissea Celestiale | 14.077 | 69 |
| Il Banchetto delle Galassie | 14.119 | 32 |
| Cosmologia Terrestre: Viaggio in Otto Dimensioni | 14.161 | 32 |
| Rinascita Cosmica | 14.203 | 59 |
| Il Rapsodo Celestiale | 14.245 | 70 |
| Bistecca Cacofonica dell'Infinito | 14.287 | 59 |
| Galassia di Sapori: Il Viaggio Senza Tempo | 14.329 | 55 |
| Pizza Cosmica all'Essenza di Drago con Nebbia Arcobaleno e Funghi Orbitali | 14.371 | 83 |
| Mycoflora con Polvere di Stelle Sbagliato | 14.413 | 62 |
| Nebulosa di Sapori dell'Infinito | 14.455 | 49 |
| Sinfonia dell'Infinito: Un Viaggio Gnodale tra Terra e Universi | 14.497 | 80 |
| Tris di Verdure con Xenodonte | 14.538 | 58 |
| Falso Risotto dell'Infinito Multiverso | 14.580 | 71 |
| Sinfonia Quantistica delle Stelle | 14.622 | 75 |
| Sinfonia Quantistica dell'Universo | 14.664 | 87 |
| Evanescenza Quantica | 14.706 | 50 |
| Galassia di Sapori Sublimi | 14.748 | 52 |
| Galassia di Sapore Quantico | 14.790 | 62 |
| Interstellare Risveglio di Kraken | 14.832 | 90 |
| Sinfonia Temporale delle Profondità Infrasoniche | 14.874 | 83 |
| Pioggia di Dimensioni Galattiche | 14.916 | 55 |
| Ode Cosmica di Terra e Stelle | 14.958 | 60 |
| Sinfonia Galattica | 15.000 | 52 |

## 07 — Preparation Time vs Number of Ingredients

- **Pearson r** = 0.0983 (p = 9.6619e-02)
- **Spearman ρ** = 0.1040 (p = 7.8717e-02)

### Mean Prep Time by Ingredient Count

|   n_ingredients |   mean |   median |   std |   count |
|----------------:|-------:|---------:|------:|--------:|
|               5 |   8.45 |     7.99 |  3.4  |      75 |
|               6 |   9.07 |     8.81 |  3.36 |      66 |
|               7 |   8.96 |     8.87 |  3.4  |      51 |
|               8 |   9.12 |     9.25 |  4.19 |      41 |
|               9 |   9.52 |     9.71 |  3.34 |      31 |
|              10 |  10.39 |    10.43 |  2.95 |      19 |
|              11 |   6.78 |     6.31 |  2.65 |       4 |

## 08 — Correlation Matrix

### Pearson Correlation

|               |   Prestige |   Prep Time (s) |   # Ingredients |
|:--------------|-----------:|----------------:|----------------:|
| Prestige      |     1      |         -0.1224 |          0.1704 |
| Prep Time (s) |    -0.1224 |          1      |          0.0983 |
| # Ingredients |     0.1704 |          0.0983 |          1      |

### Spearman Correlation

|               |   Prestige |   Prep Time (s) |   # Ingredients |
|:--------------|-----------:|----------------:|----------------:|
| Prestige      |     1      |          -0.116 |          0.1719 |
| Prep Time (s) |    -0.116  |           1     |          0.104  |
| # Ingredients |     0.1719 |           0.104 |          1      |

## 09 — Ingredient Frequency (All 62 Ingredients)

| Rank | Ingredient | Count | % of Recipes |
|------|-----------|-------|-------------|
| 1 | Carne di Balena spaziale | 65 | 22.6% |
| 2 | Carne di Kraken | 62 | 21.6% |
| 3 | Pane di Luce | 61 | 21.3% |
| 4 | Teste di Idra | 56 | 19.5% |
| 5 | Fibra di Sintetex | 54 | 18.8% |
| 6 | Carne di Drago | 54 | 18.8% |
| 7 | Uova di Fenice | 53 | 18.5% |
| 8 | Pane degli Abissi | 48 | 16.7% |
| 9 | Amido di Stellarion | 47 | 16.4% |
| 10 | Carne di Xenodonte | 47 | 16.4% |
| 11 | Riso di Cassandra | 47 | 16.4% |
| 12 | Farina di Nettuno | 46 | 16.0% |
| 13 | Lattuga Namecciana | 46 | 16.0% |
| 14 | Carne di Mucca | 46 | 16.0% |
| 15 | Granuli di Nebbia Arcobaleno | 45 | 15.7% |
| 16 | Colonia di Mycoflora | 45 | 15.7% |
| 17 | Radici di Singolarità | 45 | 15.7% |
| 18 | Baccacedro | 44 | 15.3% |
| 19 | Biscotti della Galassia | 43 | 15.0% |
| 20 | Spaghi del Sole | 43 | 15.0% |
| 21 | Foglie di Nebulosa | 42 | 14.6% |
| 22 | Fusilli del Vento | 39 | 13.6% |
| 23 | Radici di Gravità | 39 | 13.6% |
| 24 | Nettare di Sirena | 39 | 13.6% |
| 25 | Gnocchi del Crepuscolo | 38 | 13.2% |
| 26 | Lacrime di Unicorno | 36 | 12.5% |
| 27 | Foglie di Mandragora | 34 | 11.8% |
| 28 | Muffa Lunare | 32 | 11.1% |
| 29 | Liane di Plasmodio | 31 | 10.8% |
| 30 | Essenza di Tachioni | 31 | 10.8% |
| 31 | Alghe Bioluminescenti | 31 | 10.8% |
| 32 | Essenza di Vuoto | 29 | 10.1% |
| 33 | Shard di Materia Oscura | 29 | 10.1% |
| 34 | Essenza di Speziaria | 29 | 10.1% |
| 35 | Funghi dell’Etere | 29 | 10.1% |
| 36 | Funghi Orbitali | 29 | 10.1% |
| 37 | Petali di Eco | 28 | 9.8% |
| 38 | Lacrime di Andromeda | 28 | 9.8% |
| 39 | Nduja Fritta Tanto | 28 | 9.8% |
| 40 | Polvere di Stelle | 28 | 9.8% |
| 41 | Sale Temporale | 27 | 9.4% |
| 42 | Vero Ghiaccio | 27 | 9.4% |
| 43 | Polvere di Pulsar | 26 | 9.1% |
| 44 | Polvere di Crononite | 26 | 9.1% |
| 45 | Salsa Szechuan | 26 | 9.1% |
| 46 | Frammenti di Supernova | 25 | 8.7% |
| 47 | Plasma Vitale | 25 | 8.7% |
| 48 | Shard di Prisma Stellare | 24 | 8.4% |
| 49 | Cristalli di Memoria | 23 | 8.0% |
| 50 | Erba Pipa | 23 | 8.0% |
| 51 | Cristalli di Nebulite | 22 | 7.7% |
| 52 | Frutti del Diavolo | 21 | 7.3% |
| 53 | Spore Quantiche | 19 | 6.6% |
| 54 | Spezie Melange | 1 | 0.3% |
| 55 | Cioccorane | 1 | 0.3% |
| 56 | Burrobirra | 1 | 0.3% |
| 57 | Slurm | 1 | 0.3% |
| 58 | Sashimi di Magikarp | 1 | 0.3% |
| 59 | Pickle Rick Croccante | 1 | 0.3% |
| 60 | Chocobo Wings | 1 | 0.3% |
| 61 | Latte+ | 1 | 0.3% |
| 62 | Ravioli al Vaporeon | 1 | 0.3% |

## 10 — Ingredient Prestige Impact (Δ Prestige)

| Ingredient | Mean With | Mean Without | Δ | Count | p-value | Significant (p<0.05) |
|-----------|-----------|-------------|---|-------|---------|---------------------|
| Polvere di Crononite | 71.81 | 61.87 | +9.93 | 26 | 0.002 | Yes |
| Shard di Prisma Stellare | 70.88 | 62.03 | +8.84 | 24 | 0.0089 | Yes |
| Lacrime di Andromeda | 70.25 | 61.97 | +8.28 | 28 | 0.0218 | Yes |
| Frutti del Diavolo | 68.62 | 62.31 | +6.31 | 21 | 0.0623 | No |
| Essenza di Tachioni | 68.16 | 62.12 | +6.04 | 31 | 0.0395 | Yes |
| Gnocchi del Crepuscolo | 67.16 | 62.1 | +5.05 | 38 | 0.1377 | No |
| Polvere di Stelle | 67.14 | 62.3 | +4.84 | 28 | 0.1996 | No |
| Teste di Idra | 66.25 | 61.93 | +4.32 | 56 | 0.0929 | No |
| Shard di Materia Oscura | 66.31 | 62.38 | +3.93 | 29 | 0.2082 | No |
| Spore Quantiche | 66.42 | 62.51 | +3.91 | 19 | 0.2504 | No |
| Sale Temporale | 66.19 | 62.42 | +3.77 | 27 | 0.2802 | No |
| Riso di Cassandra | 65.85 | 62.17 | +3.68 | 47 | 0.2292 | No |
| Uova di Fenice | 65.72 | 62.11 | +3.61 | 53 | 0.151 | No |
| Carne di Mucca | 65.63 | 62.23 | +3.40 | 46 | 0.2596 | No |
| Spaghi del Sole | 64.95 | 62.39 | +2.56 | 43 | 0.3556 | No |
| Biscotti della Galassia | 64.91 | 62.4 | +2.51 | 43 | 0.3643 | No |
| Nduja Fritta Tanto | 64.96 | 62.54 | +2.43 | 28 | 0.4072 | No |
| Frammenti di Supernova | 64.84 | 62.58 | +2.26 | 25 | 0.5321 | No |
| Granuli di Nebbia Arcobaleno | 64.64 | 62.43 | +2.22 | 45 | 0.4254 | No |
| Petali di Eco | 64.75 | 62.56 | +2.19 | 28 | 0.4423 | No |
| Muffa Lunare | 64.53 | 62.55 | +1.98 | 32 | 0.5172 | No |
| Fibra di Sintetex | 64.0 | 62.49 | +1.51 | 54 | 0.5343 | No |
| Colonia di Mycoflora | 64.0 | 62.55 | +1.45 | 45 | 0.583 | No |
| Carne di Balena spaziale | 63.75 | 62.49 | +1.27 | 65 | 0.5824 | No |
| Amido di Stellarion | 63.43 | 62.65 | +0.78 | 47 | 0.7576 | No |
| Carne di Xenodonte | 63.38 | 62.65 | +0.73 | 47 | 0.8011 | No |
| Essenza di Vuoto | 63.41 | 62.7 | +0.71 | 29 | 0.8524 | No |
| Pane degli Abissi | 63.12 | 62.7 | +0.42 | 48 | 0.8792 | No |
| Carne di Kraken | 63.02 | 62.71 | +0.31 | 62 | 0.8967 | No |
| Radici di Singolarità | 62.78 | 62.77 | +0.01 | 45 | 0.9984 | No |
| Erba Pipa | 62.74 | 62.78 | -0.04 | 23 | 0.9909 | No |
| Plasma Vitale | 62.56 | 62.79 | -0.23 | 25 | 0.946 | No |
| Farina di Nettuno | 62.41 | 62.84 | -0.43 | 46 | 0.8766 | No |
| Cristalli di Memoria | 62.26 | 62.82 | -0.56 | 23 | 0.8779 | No |
| Liane di Plasmodio | 62.26 | 62.84 | -0.58 | 31 | 0.8554 | No |
| Foglie di Nebulosa | 62.14 | 62.88 | -0.74 | 42 | 0.8205 | No |
| Radici di Gravità | 62.13 | 62.88 | -0.75 | 39 | 0.8086 | No |
| Fusilli del Vento | 61.92 | 62.91 | -0.98 | 39 | 0.6844 | No |
| Funghi Orbitali | 61.52 | 62.91 | -1.40 | 29 | 0.7016 | No |
| Vero Ghiaccio | 61.44 | 62.91 | -1.47 | 27 | 0.6578 | No |
| Foglie di Mandragora | 61.35 | 62.96 | -1.61 | 34 | 0.6029 | No |
| Polvere di Pulsar | 61.04 | 62.95 | -1.91 | 26 | 0.6151 | No |
| Lacrime di Unicorno | 61.0 | 63.03 | -2.03 | 36 | 0.4923 | No |
| Alghe Bioluminescenti | 60.77 | 63.02 | -2.24 | 31 | 0.4851 | No |
| Baccacedro | 60.77 | 63.14 | -2.36 | 44 | 0.413 | No |
| Carne di Drago | 60.83 | 63.22 | -2.39 | 54 | 0.2997 | No |
| Nettare di Sirena | 59.72 | 63.25 | -3.54 | 39 | 0.2274 | No |
| Funghi dell’Etere | 59.59 | 63.13 | -3.55 | 29 | 0.3391 | No |
| Lattuga Namecciana | 59.76 | 63.35 | -3.59 | 46 | 0.2039 | No |
| Essenza di Speziaria | 59.07 | 63.19 | -4.12 | 29 | 0.1746 | No |
| Pane di Luce | 59.38 | 63.69 | -4.31 | 61 | 0.0545 | No |
| Cristalli di Nebulite | 56.05 | 63.33 | -7.29 | 22 | 0.0755 | No |
| Salsa Szechuan | 54.46 | 63.6 | -9.14 | 26 | 0.015 | Yes |

## 11 — Ingredient Co-occurrence Matrix (Top 20 Ingredients)

|                              |   Carne di Balena spaziale |   Carne di Kraken |   Pane di Luce |   Teste di Idra |   Fibra di Sintetex |   Carne di Drago |   Uova di Fenice |   Pane degli Abissi |   Amido di Stellarion |   Carne di Xenodonte |   Riso di Cassandra |   Farina di Nettuno |   Lattuga Namecciana |   Carne di Mucca |   Granuli di Nebbia Arcobaleno |   Colonia di Mycoflora |   Radici di Singolarità |   Baccacedro |   Biscotti della Galassia |   Spaghi del Sole |
|:-----------------------------|---------------------------:|------------------:|---------------:|----------------:|--------------------:|-----------------:|-----------------:|--------------------:|----------------------:|---------------------:|--------------------:|--------------------:|---------------------:|-----------------:|-------------------------------:|-----------------------:|------------------------:|-------------:|--------------------------:|------------------:|
| Carne di Balena spaziale     |                          0 |                16 |             19 |              14 |                  17 |               10 |               12 |                  11 |                     8 |                   10 |                   8 |                   7 |                    6 |                8 |                              9 |                      7 |                      11 |            9 |                         9 |                 8 |
| Carne di Kraken              |                         16 |                 0 |             18 |               8 |                  12 |                9 |               12 |                   9 |                    14 |                   12 |                   9 |                  11 |                    9 |               10 |                              8 |                      8 |                       7 |            5 |                         4 |                 9 |
| Pane di Luce                 |                         19 |                18 |              0 |               7 |                   9 |               18 |               11 |                  12 |                     9 |                    9 |                  11 |                   9 |                    4 |                8 |                              6 |                      9 |                      12 |           11 |                         7 |                12 |
| Teste di Idra                |                         14 |                 8 |              7 |               0 |                   9 |               13 |                6 |                   9 |                     7 |                   14 |                  12 |                  10 |                   11 |               10 |                              4 |                      8 |                       5 |            5 |                         8 |                 6 |
| Fibra di Sintetex            |                         17 |                12 |              9 |               9 |                   0 |                9 |                8 |                   8 |                     7 |                    9 |                   6 |                   9 |                    9 |               10 |                              7 |                      7 |                       6 |            7 |                         8 |                 7 |
| Carne di Drago               |                         10 |                 9 |             18 |              13 |                   9 |                0 |               11 |                   7 |                    13 |                    8 |                  12 |                   8 |                   10 |               10 |                              6 |                      6 |                       8 |            6 |                        11 |                 7 |
| Uova di Fenice               |                         12 |                12 |             11 |               6 |                   8 |               11 |                0 |                  10 |                     8 |                    5 |                   9 |                   9 |                    7 |               10 |                              8 |                      7 |                      13 |            6 |                        11 |                11 |
| Pane degli Abissi            |                         11 |                 9 |             12 |               9 |                   8 |                7 |               10 |                   0 |                     1 |                   12 |                   6 |                   6 |                    4 |                7 |                              8 |                      9 |                       2 |            8 |                         7 |                 4 |
| Amido di Stellarion          |                          8 |                14 |              9 |               7 |                   7 |               13 |                8 |                   1 |                     0 |                    8 |                   7 |                  11 |                    7 |                9 |                              7 |                      6 |                       7 |            9 |                         6 |                 5 |
| Carne di Xenodonte           |                         10 |                12 |              9 |              14 |                   9 |                8 |                5 |                  12 |                     8 |                    0 |                   6 |                   8 |                    7 |                5 |                              7 |                      6 |                       3 |            6 |                         5 |                 7 |
| Riso di Cassandra            |                          8 |                 9 |             11 |              12 |                   6 |               12 |                9 |                   6 |                     7 |                    6 |                   0 |                   8 |                    8 |               12 |                              6 |                      4 |                       9 |            4 |                         6 |                 9 |
| Farina di Nettuno            |                          7 |                11 |              9 |              10 |                   9 |                8 |                9 |                   6 |                    11 |                    8 |                   8 |                   0 |                    5 |                7 |                              6 |                      6 |                       9 |            6 |                         5 |                 8 |
| Lattuga Namecciana           |                          6 |                 9 |              4 |              11 |                   9 |               10 |                7 |                   4 |                     7 |                    7 |                   8 |                   5 |                    0 |                8 |                              7 |                      5 |                       7 |            8 |                         5 |                 7 |
| Carne di Mucca               |                          8 |                10 |              8 |              10 |                  10 |               10 |               10 |                   7 |                     9 |                    5 |                  12 |                   7 |                    8 |                0 |                              5 |                      7 |                       5 |            5 |                         9 |                 7 |
| Granuli di Nebbia Arcobaleno |                          9 |                 8 |              6 |               4 |                   7 |                6 |                8 |                   8 |                     7 |                    7 |                   6 |                   6 |                    7 |                5 |                              0 |                      7 |                      10 |           12 |                         6 |                 6 |
| Colonia di Mycoflora         |                          7 |                 8 |              9 |               8 |                   7 |                6 |                7 |                   9 |                     6 |                    6 |                   4 |                   6 |                    5 |                7 |                              7 |                      0 |                       7 |            9 |                         5 |                 7 |
| Radici di Singolarità        |                         11 |                 7 |             12 |               5 |                   6 |                8 |               13 |                   2 |                     7 |                    3 |                   9 |                   9 |                    7 |                5 |                             10 |                      7 |                       0 |           10 |                         4 |                 6 |
| Baccacedro                   |                          9 |                 5 |             11 |               5 |                   7 |                6 |                6 |                   8 |                     9 |                    6 |                   4 |                   6 |                    8 |                5 |                             12 |                      9 |                      10 |            0 |                         7 |                 8 |
| Biscotti della Galassia      |                          9 |                 4 |              7 |               8 |                   8 |               11 |               11 |                   7 |                     6 |                    5 |                   6 |                   5 |                    5 |                9 |                              6 |                      5 |                       4 |            7 |                         0 |                10 |
| Spaghi del Sole              |                          8 |                 9 |             12 |               6 |                   7 |                7 |               11 |                   4 |                     5 |                    7 |                   9 |                   8 |                    7 |                7 |                              6 |                      7 |                       6 |            8 |                        10 |                 0 |

### Top 30 Co-occurring Pairs

| Rank | Ingredient 1 | Ingredient 2 | Co-occurrences |
|------|-------------|-------------|----------------|
| 1 | Carne di Balena spaziale | Pane di Luce | 19 |
| 2 | Carne di Drago | Pane di Luce | 18 |
| 3 | Carne di Kraken | Pane di Luce | 18 |
| 4 | Carne di Balena spaziale | Fibra di Sintetex | 17 |
| 5 | Carne di Balena spaziale | Carne di Kraken | 16 |
| 6 | Amido di Stellarion | Carne di Kraken | 14 |
| 7 | Carne di Xenodonte | Teste di Idra | 14 |
| 8 | Fibra di Sintetex | Foglie di Nebulosa | 14 |
| 9 | Carne di Balena spaziale | Teste di Idra | 14 |
| 10 | Carne di Drago | Teste di Idra | 13 |
| 11 | Amido di Stellarion | Carne di Drago | 13 |
| 12 | Radici di Singolarità | Uova di Fenice | 13 |
| 13 | Carne di Xenodonte | Pane degli Abissi | 12 |
| 14 | Carne di Kraken | Carne di Xenodonte | 12 |
| 15 | Carne di Kraken | Fibra di Sintetex | 12 |
| 16 | Carne di Drago | Riso di Cassandra | 12 |
| 17 | Riso di Cassandra | Teste di Idra | 12 |
| 18 | Pane di Luce | Radici di Singolarità | 12 |
| 19 | Baccacedro | Granuli di Nebbia Arcobaleno | 12 |
| 20 | Carne di Kraken | Uova di Fenice | 12 |
| 21 | Carne di Mucca | Riso di Cassandra | 12 |
| 22 | Pane di Luce | Spaghi del Sole | 12 |
| 23 | Pane degli Abissi | Pane di Luce | 12 |
| 24 | Carne di Balena spaziale | Uova di Fenice | 12 |
| 25 | Carne di Balena spaziale | Pane degli Abissi | 11 |
| 26 | Carne di Balena spaziale | Sale Temporale | 11 |
| 27 | Lattuga Namecciana | Teste di Idra | 11 |
| 28 | Carne di Balena spaziale | Nettare di Sirena | 11 |
| 29 | Spaghi del Sole | Uova di Fenice | 11 |
| 30 | Baccacedro | Pane di Luce | 11 |

## 12 — Prestige Tier Comparison

| tier       |   count |   mean_prestige |   std_prestige |   mean_ingredients |   std_ingredients |   mean_prep_s |   std_prep_s |   min_prestige |   max_prestige |
|:-----------|--------:|----------------:|---------------:|-------------------:|------------------:|--------------:|-------------:|---------------:|---------------:|
| S (90-100) |      19 |           93.95 |           3.57 |               7.53 |              1.65 |          7.43 |         2.98 |             90 |            100 |
| A (80-89)  |      38 |           83.97 |           2.73 |               7    |              1.8  |          8.49 |         3.56 |             80 |             89 |
| B (70-79)  |      43 |           74.09 |           3.13 |               7    |              1.59 |          8.21 |         3.29 |             70 |             79 |
| C (60-69)  |      65 |           63.86 |           2.82 |               6.88 |              1.52 |          9.56 |         3.37 |             60 |             69 |
| D (50-59)  |      56 |           53.3  |           2.97 |               7.3  |              1.74 |         10.11 |         3.45 |             50 |             59 |
| E (<50)    |      66 |           41.18 |           6.79 |               6.11 |              1.33 |          8.77 |         3.57 |             23 |             49 |

## 13 — Ingredient Count by Tier (Violin Plot Data)

### Quantiles of # Ingredients per Tier

**S (90-100)** (n=19)
- Min: 5, Q1: 6.0, Median: 8.0, Q3: 9.0, Max: 10
- Distribution: 5 ing → 3 recipes, 6 ing → 3 recipes, 7 ing → 2 recipes, 8 ing → 5 recipes, 9 ing → 4 recipes, 10 ing → 2 recipes

**A (80-89)** (n=38)
- Min: 5, Q1: 5.2, Median: 6.5, Q3: 8.8, Max: 11
- Distribution: 5 ing → 10 recipes, 6 ing → 9 recipes, 7 ing → 5 recipes, 8 ing → 4 recipes, 9 ing → 6 recipes, 10 ing → 3 recipes, 11 ing → 1 recipes

**B (70-79)** (n=43)
- Min: 5, Q1: 6.0, Median: 7.0, Q3: 8.0, Max: 10
- Distribution: 5 ing → 9 recipes, 6 ing → 11 recipes, 7 ing → 6 recipes, 8 ing → 8 recipes, 9 ing → 6 recipes, 10 ing → 3 recipes

**C (60-69)** (n=65)
- Min: 5, Q1: 6.0, Median: 7.0, Q3: 8.0, Max: 11
- Distribution: 5 ing → 13 recipes, 6 ing → 15 recipes, 7 ing → 20 recipes, 8 ing → 7 recipes, 9 ing → 6 recipes, 10 ing → 2 recipes, 11 ing → 2 recipes

**D (50-59)** (n=56)
- Min: 5, Q1: 6.0, Median: 7.0, Q3: 9.0, Max: 10
- Distribution: 5 ing → 11 recipes, 6 ing → 11 recipes, 7 ing → 9 recipes, 8 ing → 8 recipes, 9 ing → 9 recipes, 10 ing → 8 recipes

**E (<50)** (n=66)
- Min: 5, Q1: 5.0, Median: 6.0, Q3: 7.0, Max: 11
- Distribution: 5 ing → 29 recipes, 6 ing → 17 recipes, 7 ing → 9 recipes, 8 ing → 9 recipes, 10 ing → 1 recipes, 11 ing → 1 recipes

## 14 — S-Tier Ingredient Enrichment

S-tier recipes: 19 (prestige ≥ 90)

| Ingredient | S-Tier Count | Total Count | % in S-Tier | % Overall | Enrichment Ratio |
|-----------|-------------|-------------|-------------|-----------|-----------------|
| Cioccorane | 1 | 1 | 5.3% | 0.3% | 15.11× |
| Lacrime di Andromeda | 6 | 28 | 31.6% | 9.8% | 3.24× |
| Polvere di Stelle | 6 | 28 | 31.6% | 9.8% | 3.24× |
| Frammenti di Supernova | 4 | 25 | 21.1% | 8.7% | 2.42× |
| Essenza di Vuoto | 4 | 29 | 21.1% | 10.1% | 2.08× |
| Carne di Mucca | 6 | 46 | 31.6% | 16.0% | 1.97× |
| Riso di Cassandra | 6 | 47 | 31.6% | 16.4% | 1.93× |
| Shard di Prisma Stellare | 3 | 24 | 15.8% | 8.4% | 1.89× |
| Plasma Vitale | 3 | 25 | 15.8% | 8.7% | 1.81× |
| Foglie di Nebulosa | 5 | 42 | 26.3% | 14.6% | 1.8× |
| Polvere di Crononite | 3 | 26 | 15.8% | 9.1% | 1.74× |
| Polvere di Pulsar | 3 | 26 | 15.8% | 9.1% | 1.74× |
| Teste di Idra | 6 | 56 | 31.6% | 19.5% | 1.62× |
| Carne di Xenodonte | 5 | 47 | 26.3% | 16.4% | 1.61× |
| Gnocchi del Crepuscolo | 4 | 38 | 21.1% | 13.2% | 1.59× |
| Uova di Fenice | 5 | 53 | 26.3% | 18.5% | 1.43× |
| Spaghi del Sole | 4 | 43 | 21.1% | 15.0% | 1.41× |
| Carne di Kraken | 5 | 62 | 26.3% | 21.6% | 1.22× |
| Carne di Balena spaziale | 5 | 65 | 26.3% | 22.6% | 1.16× |
| Sale Temporale | 2 | 27 | 10.5% | 9.4% | 1.12× |
| Fibra di Sintetex | 4 | 54 | 21.1% | 18.8% | 1.12× |
| Vero Ghiaccio | 2 | 27 | 10.5% | 9.4% | 1.12× |
| Nduja Fritta Tanto | 2 | 28 | 10.5% | 9.8% | 1.08× |
| Funghi dell’Etere | 2 | 29 | 10.5% | 10.1% | 1.04× |
| Shard di Materia Oscura | 2 | 29 | 10.5% | 10.1% | 1.04× |
| Colonia di Mycoflora | 3 | 45 | 15.8% | 15.7% | 1.01× |
| Farina di Nettuno | 3 | 46 | 15.8% | 16.0% | 0.99× |
| Alghe Bioluminescenti | 2 | 31 | 10.5% | 10.8% | 0.97× |
| Amido di Stellarion | 3 | 47 | 15.8% | 16.4% | 0.96× |
| Pane degli Abissi | 3 | 48 | 15.8% | 16.7% | 0.94× |
| Muffa Lunare | 2 | 32 | 10.5% | 11.1% | 0.94× |
| Lacrime di Unicorno | 2 | 36 | 10.5% | 12.5% | 0.84× |
| Nettare di Sirena | 2 | 39 | 10.5% | 13.6% | 0.77× |
| Radici di Gravità | 2 | 39 | 10.5% | 13.6% | 0.77× |
| Pane di Luce | 3 | 61 | 15.8% | 21.3% | 0.74× |
| Frutti del Diavolo | 1 | 21 | 5.3% | 7.3% | 0.72× |
| Biscotti della Galassia | 2 | 43 | 10.5% | 15.0% | 0.7× |
| Baccacedro | 2 | 44 | 10.5% | 15.3% | 0.69× |
| Granuli di Nebbia Arcobaleno | 2 | 45 | 10.5% | 15.7% | 0.67× |
| Lattuga Namecciana | 2 | 46 | 10.5% | 16.0% | 0.66× |
| Erba Pipa | 1 | 23 | 5.3% | 8.0% | 0.66× |
| Cristalli di Memoria | 1 | 23 | 5.3% | 8.0% | 0.66× |
| Carne di Drago | 2 | 54 | 10.5% | 18.8% | 0.56× |
| Petali di Eco | 1 | 28 | 5.3% | 9.8% | 0.54× |
| Funghi Orbitali | 1 | 29 | 5.3% | 10.1% | 0.52× |
| Essenza di Tachioni | 1 | 31 | 5.3% | 10.8% | 0.49× |
| Liane di Plasmodio | 1 | 31 | 5.3% | 10.8% | 0.49× |
| Foglie di Mandragora | 1 | 34 | 5.3% | 11.8% | 0.44× |
| Fusilli del Vento | 1 | 39 | 5.3% | 13.6% | 0.39× |
| Radici di Singolarità | 1 | 45 | 5.3% | 15.7% | 0.34× |

### Ingredients ABSENT from all S-Tier Recipes

| Ingredient | Total Count |
|-----------|-------------|
| Essenza di Speziaria | 29 |
| Salsa Szechuan | 26 |
| Cristalli di Nebulite | 22 |
| Spore Quantiche | 19 |
| Spezie Melange | 1 |
| Burrobirra | 1 |
| Slurm | 1 |
| Sashimi di Magikarp | 1 |
| Pickle Rick Croccante | 1 |
| Chocobo Wings | 1 |
| Latte+ | 1 |
| Ravioli al Vaporeon | 1 |

## 15 — Prestige Efficiency

### All Recipes Ranked by Prestige per Ingredient

| Recipe | Prestige | # Ing | Prestige/Ing | Prep (s) | Prestige/Sec |
|--------|----------|-------|-------------|----------|-------------|
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sf | 100 | 5 | 20.0 | 5.224 | 19.14 |
| Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plas | 95 | 5 | 19.0 | 4.049 | 23.46 |
| Sinfonia di Multiverso: La Danza degli Elementi | 90 | 5 | 18.0 | 5.559 | 16.19 |
| Viaggio Cosmico nel Multiverso | 89 | 5 | 17.8 | 6.860 | 12.97 |
| Sinfonia Aromatica del Multiverso | 89 | 5 | 17.8 | 6.650 | 13.38 |
| Piastrella Celestiale di Gnocchi del Crepuscolo con Nebulosa di Riso di Cassandr | 86 | 5 | 17.2 | 10.846 | 7.93 |
| Sinfonia Cosmica di Andromeda | 85 | 5 | 17.0 | 9.210 | 9.23 |
| Sinfonia Cosmica di Terracotta | 85 | 5 | 17.0 | 6.818 | 12.47 |
| Sinfonia del Multiverso Calante | 85 | 5 | 17.0 | 3.965 | 21.44 |
| Sinfonia Temporale delle Profondità Infrasoniche | 83 | 5 | 16.6 | 14.874 | 5.58 |
| Sinfonia Cosmica: il Ritorno dell'Imperatore | 82 | 5 | 16.4 | 11.601 | 7.07 |
| Sinfonia del Multiverso | 80 | 5 | 16.0 | 5.517 | 14.5 |
| Galassia di Sapori: Sinfonia Transdimensionale | 80 | 5 | 16.0 | 11.853 | 6.75 |
| Più-dimensionale Sinfonia di Sapori: La Carne del Cosmo | 95 | 6 | 15.83 | 4.846 | 19.6 |
| Sinfonia Quantica dell'Oceano Interstellare | 94 | 6 | 15.67 | 4.007 | 23.46 |
| Sinfonia Celestiale di Echi Galattici | 77 | 5 | 15.4 | 9.336 | 8.25 |
| Sinfonia Cosmica di Mare e Stelle | 77 | 5 | 15.4 | 4.594 | 16.76 |
| Sinfonia Cosmica di Proteine Interstellari | 77 | 5 | 15.4 | 3.042 | 25.31 |
| Sinfonia Celeste dell'Equilibrio Temporale | 92 | 6 | 15.33 | 9.420 | 9.77 |
| Nebulosa di Fenice con Sinfonia Eterea | 75 | 5 | 15.0 | 6.189 | 12.12 |
| Sinfonia Celestiale di Gnocchi del Crepuscolo | 88 | 6 | 14.67 | 4.469 | 19.69 |
| Sinfonia Cosmica: la Vendetta Fantasma | 73 | 5 | 14.6 | 11.517 | 6.34 |
| Galassia nel Piatto: Sinfonia di Sapori e Dimensioni | 87 | 6 | 14.5 | 9.839 | 8.84 |
| Portale del Cosmo: Sinfonia di Sapori Multidimensionali | 72 | 5 | 14.4 | 5.769 | 12.48 |
| Galassia di Sapore Quantum | 72 | 5 | 14.4 | 7.825 | 9.2 |
| Sinfonia Cosmica del Multiverso | 100 | 7 | 14.29 | 5.643 | 17.72 |
| Sinfonia Cosmica all'Alba di Fenice | 85 | 6 | 14.17 | 13.867 | 6.13 |
| Sinfonia del Multiverso Nascente | 84 | 6 | 14.0 | 3.797 | 22.12 |
| Eterea Sinfonia di Gravità con Infusione Temporale | 84 | 6 | 14.0 | 3.462 | 24.26 |
| Sinfonia Cosmica: Versione Data | 84 | 6 | 14.0 | 5.266 | 15.95 |
| Sinfonia dei Ricordi Celesti | 70 | 5 | 14.0 | 11.937 | 5.86 |
| Sinfonia Celeste di Granuli Arcobaleno e Riso di Cassandra | 70 | 5 | 14.0 | 10.888 | 6.43 |
| Nebulosa di Dragone all'Essenza di Vuoto | 69 | 5 | 13.8 | 10.762 | 6.41 |
| Sinfonia Cosmica ma Fatta Bene | 82 | 6 | 13.67 | 7.406 | 11.07 |
| Galassia a Tavola: Sinfonia di Tempeste Cosmiche | 82 | 6 | 13.67 | 8.035 | 10.21 |
| Armonia Cosmica alla Tavola d'Oro | 68 | 5 | 13.6 | 4.343 | 15.66 |
| Sinfonia Cosmologica | 68 | 5 | 13.6 | 5.308 | 12.81 |
| Viaggio dei Sensi: Bolla Temporale di Aromi Ancestrali | 67 | 5 | 13.4 | 6.105 | 10.97 |
| Sinfonia dell'Infinito: Un Viaggio Gnodale tra Terra e Universi | 80 | 6 | 13.33 | 14.497 | 5.52 |
| Sinfonia Cosmica di Aurora | 66 | 5 | 13.2 | 8.748 | 7.54 |
| Sinfonia Interstellare di Fusilli del Vento con Nettare di Sirena | 79 | 6 | 13.17 | 6.524 | 12.11 |
| Sinfonia di Crepuscolo Celestiale | 79 | 6 | 13.17 | 6.021 | 13.12 |
| Galassia in Tavola: Sinfonia dei Sensi | 65 | 5 | 13.0 | 13.322 | 4.88 |
| Armonia Cosmica della Fenice | 78 | 6 | 13.0 | 7.699 | 10.13 |
| Sinfonia Cosmica di Armonie Terrestri e Celesti | 90 | 7 | 12.86 | 5.350 | 16.82 |
| Sinfonia Temporale nello Spaghi del Sole | 77 | 6 | 12.83 | 5.979 | 12.88 |
| Risveglio Cosmico: Un Viaggio nel Sapore Quantistico | 76 | 6 | 12.67 | 12.776 | 5.95 |
| Sinfonia di Galassie Perdute | 63 | 5 | 12.6 | 9.000 | 7.0 |
| Plasma Celestiale al Risotto di Kraken nell'Aura del Sole | 88 | 7 | 12.57 | 4.888 | 18.0 |
| Mycoflora con Polvere di Stelle Sbagliato | 62 | 5 | 12.4 | 14.413 | 4.3 |
| Universo in Fusilli - Variazione Celestiale | 62 | 5 | 12.4 | 3.503 | 17.7 |
| Sinfonia Crepuscolare | 61 | 5 | 12.2 | 12.147 | 5.02 |
| Sinfonia Galattica ai Cristalli di Nebulite | 73 | 6 | 12.17 | 5.811 | 12.56 |
| Sinfonia Temporale Galattica | 73 | 6 | 12.17 | 10.007 | 7.29 |
| Sinfonia Cosmica: La Danza dell'Universo | 96 | 8 | 12.0 | 9.545 | 10.06 |
| Interstellar Requiem | 60 | 5 | 12.0 | 9.587 | 6.26 |
| Risotto Cosmico Multiversale | 60 | 5 | 12.0 | 4.678 | 12.83 |
| Danza Cosmica al Crepuscolo | 60 | 5 | 12.0 | 10.133 | 5.92 |
| Cosmic Synchrony: Il Destino di Pulsar | 72 | 6 | 12.0 | 3.168 | 22.73 |
| Galassie Infiammate: Sinfonia Cosmica in Sei Dimensioni | 95 | 8 | 11.88 | 7.280 | 13.05 |
| Galassia di Celestial Delight | 71 | 6 | 11.83 | 8.161 | 8.7 |
| Sinfonia Astrale | 82 | 7 | 11.71 | 10.175 | 8.06 |
| Sinfonia Temporale del Drago | 82 | 7 | 11.71 | 4.133 | 19.84 |
| Sinfonia Galattica alla Griglia Cangiante | 70 | 6 | 11.67 | 7.238 | 9.67 |
| Sinfonia del Cosmo Rigenerante | 70 | 6 | 11.67 | 6.315 | 11.08 |
| Mandragola e Radici | 58 | 5 | 11.6 | 13.154 | 4.41 |
| Sinfonia Cosmica di Luminiscenze e Contrasti | 81 | 7 | 11.57 | 5.140 | 15.76 |
| Risveglio Cosmico: Una Sinfonia di Sapori Universali | 92 | 8 | 11.5 | 9.252 | 9.94 |
| Sinfonia Cosmica di Sapore | 80 | 7 | 11.43 | 5.098 | 15.69 |
| Cosmic Harmony | 57 | 5 | 11.4 | 13.238 | 4.31 |
| Sinfonia del Cosmo e della Leggenda | 57 | 5 | 11.4 | 4.762 | 11.97 |
| Sinfonia Galattica di Sapori con Sorpresa di Drago Fiammante | 68 | 6 | 11.33 | 11.727 | 5.8 |
| Interstellare Risveglio di Kraken | 90 | 8 | 11.25 | 14.832 | 6.07 |
| Sinfonia Cosmica in Otto Movimenti | 90 | 8 | 11.25 | 5.182 | 17.37 |
| Universo Incantato: Sinfonia dei Gusti Cosmogonici | 67 | 6 | 11.17 | 11.308 | 5.93 |
| Galassia Infinita: Viaggio tra Memorie e Stelle | 67 | 6 | 11.17 | 8.664 | 7.73 |
| Sinfonia di Gusti del Multiverso | 67 | 6 | 11.17 | 5.727 | 11.7 |
| Viaggio Cosmico tra Mare e Stelle | 78 | 7 | 11.14 | 10.720 | 7.28 |
| Sinfonia Celestiale | 89 | 8 | 11.12 | 8.371 | 10.63 |
| Sinfonia Astrale - Risotto Multiversale con Risacca Celeste | 100 | 9 | 11.11 | 9.965 | 10.04 |
| Sinfonia Galattica Agentica | 55 | 5 | 11.0 | 11.056 | 4.97 |
| Cosmos Quantum Fusion | 55 | 5 | 11.0 | 4.804 | 11.45 |
| Risveglio Cosmico | 77 | 7 | 11.0 | 9.755 | 7.89 |
| Risotto Interdimensionale alla Carne di Drago e Balena Spaziale con Biscotti del | 88 | 8 | 11.0 | 4.930 | 17.85 |
| Cosmic Harmony Risotto | 55 | 5 | 11.0 | 8.119 | 6.77 |
| Cosmic Symphony di Ghiaccio e Fuoco | 66 | 6 | 11.0 | 14.035 | 4.7 |
| Eclissi del Drago nell'Abbraccio del Kraken | 66 | 6 | 11.0 | 10.972 | 6.02 |
| Valzer Cosmico di Asteria | 65 | 6 | 10.83 | 8.622 | 7.54 |
| Sinfonia Cosmica di Terre e Stelle | 65 | 6 | 10.83 | 12.692 | 5.12 |
| Galassie in Epifania: Risotto Celestiale con Preziosi dell'Universo | 97 | 9 | 10.78 | 9.084 | 10.68 |
| Sinfonia dell'Universo Morente | 75 | 7 | 10.71 | 11.476 | 6.54 |
| Danza Luminosa del Multiverso | 53 | 5 | 10.6 | 6.944 | 7.63 |
| Sinfonia del Multiverso di Gusto | 74 | 7 | 10.57 | 10.049 | 7.36 |
| Viaggio Celeste nel Multiverso | 74 | 7 | 10.57 | 5.685 | 13.02 |
| Sinfonia Cosmica alla Szechuan | 63 | 6 | 10.5 | 13.909 | 4.53 |
| Enigma Celeste | 52 | 5 | 10.4 | 7.951 | 6.54 |
| Nebulosa di Drago Interdimensionale | 52 | 5 | 10.4 | 9.503 | 5.47 |
| Portale Interdimensionale di Sapori | 62 | 6 | 10.33 | 6.441 | 9.63 |
| Il Viaggio Cosmico di Marinetti | 62 | 6 | 10.33 | 10.804 | 5.74 |
| Sinfonia del Cosmo | 51 | 5 | 10.2 | 11.979 | 4.26 |
| Galassia di Cosmo-Delizie | 61 | 6 | 10.17 | 13.699 | 4.45 |
| Falso Risotto dell'Infinito Multiverso | 71 | 7 | 10.14 | 14.580 | 4.87 |
| Sinfonia Celestiale dei Ricordi | 81 | 8 | 10.12 | 12.189 | 6.65 |
| Sinfonia Cosmica di Sapori | 81 | 8 | 10.12 | 8.413 | 9.63 |
| Nebulosa Celestiale alla Stellaris | 90 | 9 | 10.0 | 7.112 | 12.65 |
| Serenata del Multiverso | 60 | 6 | 10.0 | 6.692 | 8.97 |
| Galassia di Sapore Interdimensionale | 60 | 6 | 10.0 | 11.811 | 5.08 |
| Nebulose Pensanti: Sinfonia del Multiverso | 90 | 9 | 10.0 | 7.070 | 12.73 |
| Galassie Sospese: Un Viaggio di Sapori Cosmogalattici | 60 | 6 | 10.0 | 7.322 | 8.19 |
| Portale di Sapori Arcani | 50 | 5 | 10.0 | 12.860 | 3.89 |
| Galassia Commovente di Stellari | 79 | 8 | 9.88 | 7.490 | 10.55 |
| Ode al Crepuscolo del Multiverso | 69 | 7 | 9.86 | 6.483 | 10.64 |
| Odissea Cosmica di Nettuno | 49 | 5 | 9.8 | 7.448 | 6.58 |
| Lumière Cosmica | 49 | 5 | 9.8 | 12.734 | 3.85 |
| Cosmic Rhapsody | 49 | 5 | 9.8 | 8.287 | 5.91 |
| Nebulosa di Sapori dell'Infinito | 49 | 5 | 9.8 | 14.455 | 3.39 |
| Viaggio Gastronomico tra le Stelle | 49 | 5 | 9.8 | 6.273 | 7.81 |
| Portale delle Stelle | 49 | 5 | 9.8 | 10.636 | 4.61 |
| Sinfonia Quantica Galattica | 49 | 5 | 9.8 | 11.014 | 4.45 |
| Sinfonia Quantistica dell'Universo | 87 | 9 | 9.67 | 14.664 | 5.93 |
| Sinfonia di Galassie Riflesse | 67 | 7 | 9.57 | 8.580 | 7.81 |
| Quadrifonia Cosmica: Sinfonia di Sapori e Dimensioni | 95 | 10 | 9.5 | 12.650 | 7.51 |
| Sinfonia Cosmica | 85 | 9 | 9.44 | 10.091 | 8.42 |
| Sinfonia di Stagioni Stellari | 85 | 9 | 9.44 | 6.063 | 14.02 |
| Creazione Celestiale: L'Alba del Cosmo | 66 | 7 | 9.43 | 8.245 | 8.0 |
| Eterna Sinfonia del Cosmo | 66 | 7 | 9.43 | 8.706 | 7.58 |
| La Mucca Che Stordisce l'Universo | 66 | 7 | 9.43 | 13.406 | 4.92 |
| Galassia Suprema | 66 | 7 | 9.43 | 9.126 | 7.23 |
| Il Crepuscolo dell’Unicorno | 47 | 5 | 9.4 | 3.210 | 14.64 |
| Galassia di Sapore Interstellare | 94 | 10 | 9.4 | 5.056 | 18.59 |
| Echi del Mare Eterno | 47 | 5 | 9.4 | 4.217 | 11.15 |
| Il Risveglio del Multiverso | 47 | 5 | 9.4 | 4.720 | 9.96 |
| Sinfonia di Cristalli e Rigenerazione | 75 | 8 | 9.38 | 5.434 | 13.8 |
| Viaggio Galattico: Sinfonia dei Sensi | 75 | 8 | 9.38 | 3.126 | 23.99 |
| Sinfonia Quantistica delle Stelle | 75 | 8 | 9.38 | 14.622 | 5.13 |
| Ecosistema Celeste | 56 | 6 | 9.33 | 3.587 | 15.61 |
| Universo in Fluttuazione | 56 | 6 | 9.33 | 9.923 | 5.64 |
| Rivelazione del Multiverso | 65 | 7 | 9.29 | 10.469 | 6.21 |
| Viaggio dei Ricordi Stellari | 65 | 7 | 9.29 | 12.105 | 5.37 |
| Evanescenza Cosmica | 65 | 7 | 9.29 | 11.643 | 5.58 |
| Cosmic Serenade | 65 | 7 | 9.29 | 3.545 | 18.34 |
| Galassia Incantata: Un Viaggio Attraverso l'Infinito | 74 | 8 | 9.25 | 9.294 | 7.96 |
| Galassia nel Piatto: Sinfonia Universale di Aromi e Sapori | 83 | 9 | 9.22 | 11.685 | 7.1 |
| Stellar Fusion | 46 | 5 | 9.2 | 10.594 | 4.34 |
| Pioggia di Dimensioni Galattiche | 55 | 6 | 9.17 | 14.916 | 3.69 |
| Galassia Sensoriale | 55 | 6 | 9.17 | 13.783 | 3.99 |
| Cosmic Harmony Infusion | 64 | 7 | 9.14 | 11.224 | 5.7 |
| Sinfonia Cosmica ma Fatta Male | 64 | 7 | 9.14 | 7.154 | 8.95 |
| Euforia Cosmica | 64 | 7 | 9.14 | 6.734 | 9.5 |
| Crescendo Cosmico | 64 | 7 | 9.14 | 8.832 | 7.25 |
| Universo Cosmico nel Piatto | 73 | 8 | 9.12 | 3.713 | 19.66 |
| Galassia di Sapori Interstellari | 82 | 9 | 9.11 | 10.343 | 7.93 |
| Delizia Astrale all'Essenza del Multiverso | 82 | 9 | 9.11 | 6.357 | 12.9 |
| Sfogliare Galattico di Sogni Temporali | 54 | 6 | 9.0 | 6.147 | 8.78 |
| Antipasto Stellare dell'Eterna Armonia | 72 | 8 | 9.0 | 3.839 | 18.75 |
| L'Estasi Cosmica di Nova | 63 | 7 | 9.0 | 3.084 | 20.43 |
| La Balena Sputafuoco | 45 | 5 | 9.0 | 13.573 | 3.32 |
| Nebulosa Celestiale di Sogni Quantici | 71 | 8 | 8.88 | 3.671 | 19.34 |
| Galassia di Sapore Quantico | 62 | 7 | 8.86 | 14.790 | 4.19 |
| Pioggia Calante dell'Universo | 62 | 7 | 8.86 | 8.203 | 7.56 |
| Aurora del Cosmo | 53 | 6 | 8.83 | 9.797 | 5.41 |
| Galaxia Rinasciata | 44 | 5 | 8.8 | 13.196 | 3.33 |
| Più Lontano delle Stelle | 44 | 5 | 8.8 | 5.601 | 7.86 |
| Galassia di Sapori | 44 | 5 | 8.8 | 10.552 | 4.17 |
| Rintocchi del Cosmo | 44 | 5 | 8.8 | 4.301 | 10.23 |
| Sinfonia Cosmica: Versione Pizza | 79 | 9 | 8.78 | 5.014 | 15.76 |
| Nebulose della Fenice su Vento Lunare | 61 | 7 | 8.71 | 7.028 | 8.68 |
| Sinfonia Cosmica della Rinascita | 78 | 9 | 8.67 | 10.510 | 7.42 |
| Piccola Odissea Cosmica | 52 | 6 | 8.67 | 13.448 | 3.87 |
| Galassia di Sapori Sublimi | 52 | 6 | 8.67 | 14.748 | 3.53 |
| Galassia di Sogni Cosmogastronomici | 52 | 6 | 8.67 | 8.455 | 6.15 |
| Galassia di Sapori di Aurora | 52 | 6 | 8.67 | 11.769 | 4.42 |
| Odissea Celestiale | 69 | 8 | 8.62 | 14.077 | 4.9 |
| Risotto dei Multiversi | 43 | 5 | 8.6 | 7.531 | 5.71 |
| Odissea Temporale | 60 | 7 | 8.57 | 4.259 | 14.09 |
| La Balena incontra la Mandragora | 60 | 7 | 8.57 | 7.657 | 7.84 |
| La Sinfonia dell'Universo | 68 | 8 | 8.5 | 11.434 | 5.95 |
| Sinfonia Temporale al Tocco di Crono | 85 | 10 | 8.5 | 6.231 | 13.64 |
| Sinfonia Cosmica: Il Crescendo delle Stelle | 84 | 10 | 8.4 | 13.951 | 6.02 |
| Galassia d'Aromi Perduti | 42 | 5 | 8.4 | 7.993 | 5.25 |
| Porta Celestiale alle Stelle | 50 | 6 | 8.33 | 9.378 | 5.33 |
| Pizza Cosmica all'Essenza di Drago con Nebbia Arcobaleno e Funghi Orbitali | 83 | 10 | 8.3 | 14.371 | 5.78 |
| Concordanza Cosmica | 65 | 8 | 8.12 | 11.266 | 5.77 |
| Sinfonia Multiversale in Otto Movimenti | 56 | 7 | 8.0 | 11.392 | 4.92 |
| Galassia Riflessa | 56 | 7 | 8.0 | 7.909 | 7.08 |
| Sogni di Abisso Cosmico | 56 | 7 | 8.0 | 10.678 | 5.24 |
| Galassia di Sapori Eterei | 56 | 7 | 8.0 | 11.098 | 5.05 |
| Astro-Risotto alle Onde Temporali | 40 | 5 | 8.0 | 7.196 | 5.56 |
| Portale Cosmico del Kraken | 79 | 10 | 7.9 | 12.944 | 6.1 |
| Nebulosa Celeste di Terrafirma | 47 | 6 | 7.83 | 9.881 | 4.76 |
| Portale Astrale di Sapori | 47 | 6 | 7.83 | 8.077 | 5.82 |
| Galassia Risvegliata | 47 | 6 | 7.83 | 5.937 | 7.92 |
| Sinfonia degli Elementi Eterni | 70 | 9 | 7.78 | 9.042 | 7.74 |
| Il Risveglio del Drago Celeste | 70 | 9 | 7.78 | 11.140 | 6.28 |
| Il Rapsodo Celestiale | 70 | 9 | 7.78 | 14.245 | 4.91 |
| Melodia del Multiverso Parallelo | 70 | 9 | 7.78 | 6.399 | 10.94 |
| Cosmos Risotto Reale | 46 | 6 | 7.67 | 7.615 | 6.04 |
| Galassia di Sapore | 61 | 8 | 7.62 | 3.252 | 18.76 |
| Risotto Cosmico alla Draconia | 68 | 9 | 7.56 | 13.028 | 5.22 |
| Galassie Riflesse: Sinfonia del Multiverso | 83 | 11 | 7.55 | 6.776 | 12.25 |
| Ode Cosmica di Terra e Stelle | 60 | 8 | 7.5 | 14.958 | 4.01 |
| Portale del Cosmo: Sinfonia di Sapori e Tempi | 75 | 10 | 7.5 | 8.916 | 8.41 |
| Rivisitazione del Kraken sotto Molecole | 60 | 8 | 7.5 | 8.329 | 7.2 |
| Echi del Cosmo | 45 | 6 | 7.5 | 4.385 | 10.26 |
| Antipasto Celestiale | 60 | 8 | 7.5 | 11.559 | 5.19 |
| Sinfonia Galattica | 52 | 7 | 7.43 | 15.000 | 3.47 |
| Simfonia Celeste di Aurora | 52 | 7 | 7.43 | 8.874 | 5.86 |
| Bistecca Cacofonica dell'Infinito | 59 | 8 | 7.38 | 14.287 | 4.13 |
| Rinascita Cosmica | 59 | 8 | 7.38 | 14.203 | 4.15 |
| Galassia di Fusilli Sferici alla Risonanza Crononica | 59 | 8 | 7.38 | 13.070 | 4.51 |
| Pizza Raul | 44 | 6 | 7.33 | 12.441 | 3.54 |
| Pizza Gio | 44 | 6 | 7.33 | 12.315 | 3.57 |
| Tris di Verdure con Xenodonte | 58 | 8 | 7.25 | 14.538 | 3.99 |
| La Creazione di Nova | 58 | 8 | 7.25 | 3.420 | 16.96 |
| Essenze dell'Infinito | 36 | 5 | 7.2 | 3.881 | 9.28 |
| Pizza Emma | 43 | 6 | 7.17 | 12.357 | 3.48 |
| Evanescenza Quantica | 50 | 7 | 7.14 | 14.706 | 3.4 |
| Galassia Rinascente | 50 | 7 | 7.14 | 13.112 | 3.81 |
| Alternate Realities Risotto | 50 | 7 | 7.14 | 4.972 | 10.06 |
| Galassie alla Spirale di Vento con Sfera di Ghiaccio Eterno | 64 | 9 | 7.11 | 13.364 | 4.79 |
| Galassia di Sapori: L'Eterno Ritorno | 71 | 10 | 7.1 | 10.427 | 6.81 |
| La Voce del Vento | 35 | 5 | 7.0 | 6.566 | 5.33 |
| Il Ricordo del Fuoco Celeste | 49 | 7 | 7.0 | 11.895 | 4.12 |
| Galaxia Gustativa | 35 | 5 | 7.0 | 8.790 | 3.98 |
| Rapsodia Quantistica nel Cosmo | 35 | 5 | 7.0 | 7.783 | 4.5 |
| L'Abbraccio del Cosmo | 35 | 5 | 7.0 | 11.182 | 3.13 |
| Fenice sull'Orizzonte degli Eventi | 63 | 9 | 7.0 | 12.902 | 4.88 |
| Galassia Ardente | 62 | 9 | 6.89 | 13.657 | 4.54 |
| Universo in Un Boccone | 62 | 9 | 6.89 | 3.629 | 17.08 |
| Cosmopolis delle Galassie Perdute | 55 | 8 | 6.88 | 5.895 | 9.33 |
| Galassia Speculare | 48 | 7 | 6.86 | 3.755 | 12.78 |
| Dimensioni del Mare Stellato | 34 | 5 | 6.8 | 6.902 | 4.93 |
| Nebulosa di Sapori Quantici | 34 | 5 | 6.8 | 13.280 | 2.56 |
| Luce e Ombra di Nomea Spaziale | 40 | 6 | 6.67 | 3.378 | 11.84 |
| Cosmofantasia di Terra e Mare nel Vortice delle Stelle | 60 | 9 | 6.67 | 13.993 | 4.29 |
| Rapsodia dei Ricordi Celesti | 46 | 7 | 6.57 | 12.021 | 3.83 |
| L'Unicorno piange il Kraken | 52 | 8 | 6.5 | 13.490 | 3.85 |
| Sfere del Ricordo Astrale | 39 | 6 | 6.5 | 12.231 | 3.19 |
| Cosmologia Terrestre: Viaggio in Otto Dimensioni | 32 | 5 | 6.4 | 14.161 | 2.26 |
| Entropia Eterna | 38 | 6 | 6.33 | 8.497 | 4.47 |
| Una Mucca e una Balena nella Singolarità | 63 | 10 | 6.3 | 12.986 | 4.85 |
| Nebulosa di Confini Sfondati | 50 | 8 | 6.25 | 13.741 | 3.64 |
| Pioggia di Andromeda | 56 | 9 | 6.22 | 7.364 | 7.6 |
| Nebulosa Galattica | 31 | 5 | 6.2 | 3.000 | 10.33 |
| Fusione Celeste | 62 | 10 | 6.2 | 9.168 | 6.76 |
| Il Risveglio delle Stelle | 37 | 6 | 6.17 | 9.462 | 3.91 |
| Il Viaggio Celeste | 49 | 8 | 6.12 | 3.336 | 14.69 |
| Il Viaggio dell'Etereo Risveglio | 55 | 9 | 6.11 | 4.552 | 12.08 |
| Il Viaggio delle Dimensioni Confluenti | 55 | 9 | 6.11 | 4.175 | 13.17 |
| Galassia di Sapori: Il Viaggio Senza Tempo | 55 | 9 | 6.11 | 14.329 | 3.84 |
| Sassi e Sassolini | 36 | 6 | 6.0 | 13.615 | 2.64 |
| Cosmos in Tavola | 42 | 7 | 6.0 | 10.930 | 3.84 |
| Galassia Aurorale | 66 | 11 | 6.0 | 10.385 | 6.36 |
| Cosmopastico di Meraviglie Celesti | 42 | 7 | 6.0 | 13.825 | 3.04 |
| Il Simposio degli Infiniti Ricordi | 48 | 8 | 6.0 | 12.063 | 3.98 |
| L'Ascensione Siderale | 47 | 8 | 5.88 | 12.818 | 3.67 |
| Il Risveglio della Fenice sull'Arcobaleno d'Oceano | 47 | 8 | 5.88 | 3.294 | 14.27 |
| Fenice Galattica | 35 | 6 | 5.83 | 7.741 | 4.52 |
| Sinfonia Tempolare Galattica | 64 | 11 | 5.82 | 5.853 | 10.93 |
| Pizza Fra | 46 | 8 | 5.75 | 12.273 | 3.75 |
| Etereo Crepuscolare | 28 | 5 | 5.6 | 3.923 | 7.14 |
| Valzer delle Stelle | 50 | 9 | 5.56 | 8.538 | 5.86 |
| Pizza Baby Simone e Alessandro | 50 | 9 | 5.56 | 12.608 | 3.97 |
| Nebulosa Eterna | 50 | 9 | 5.56 | 9.713 | 5.15 |
| Tris di Carne con Pane | 50 | 9 | 5.56 | 7.867 | 6.36 |
| Nebulose a Strati | 50 | 9 | 5.56 | 6.608 | 7.57 |
| Ethereal Temporal Elixir | 44 | 8 | 5.5 | 4.427 | 9.94 |
| Nebulosa dell'Infinito: Un Viaggio attraverso il Cosmo del Gusto | 54 | 10 | 5.4 | 9.671 | 5.58 |
| Nebulae Di-Cedri Risvegliati | 37 | 7 | 5.29 | 9.629 | 3.84 |
| L'Eternità al Crepuscolo | 36 | 7 | 5.14 | 13.531 | 2.66 |
| Panetto di Carne | 40 | 8 | 5.0 | 7.573 | 5.28 |
| Pane e Carne Rivisitato | 50 | 10 | 5.0 | 4.636 | 10.79 |
| Stella Nova | 40 | 8 | 5.0 | 5.476 | 7.3 |
| Microcosmo in un Boccone | 50 | 10 | 5.0 | 6.986 | 7.16 |
| Verso l'Inedito Oltre | 30 | 6 | 5.0 | 8.958 | 3.35 |
| Pizza Baby Lorenzo | 50 | 10 | 5.0 | 12.566 | 3.98 |
| Pizza Baby Daniele | 50 | 10 | 5.0 | 12.524 | 3.99 |
| Pizza Cri | 50 | 10 | 5.0 | 12.483 | 4.01 |
| Cosmos Culinary Symphony | 50 | 10 | 5.0 | 10.259 | 4.87 |
| Portale delle Meraviglie | 50 | 10 | 5.0 | 10.301 | 4.85 |
| Cosmo Sferico di Sogni Rigenerativi | 34 | 7 | 4.86 | 5.392 | 6.31 |
| Eclissi Quantica: Viaggio nei Reami del Gusto | 47 | 10 | 4.7 | 11.350 | 4.14 |
| Eclissi Armonica di Sapori | 29 | 7 | 4.14 | 4.510 | 6.43 |
| Il Banchetto delle Galassie | 32 | 8 | 4.0 | 14.119 | 2.27 |
| Pizza Luca | 23 | 6 | 3.83 | 12.399 | 1.85 |
| Dimensioni di Sapori Infusi | 23 | 6 | 3.83 | 10.217 | 2.25 |
| Nebulare Asteroideo con Crepuscolo di Mucca | 40 | 11 | 3.64 | 4.091 | 9.78 |

### All Recipes Ranked by Prestige per Second

| Recipe | Prestige | Prep (s) | Prestige/Sec | # Ing | Prestige/Ing |
|--------|----------|----------|-------------|-------|-------------|
| Sinfonia Cosmica di Proteine Interstellari | 77 | 3.042 | 25.31 | 5 | 15.4 |
| Eterea Sinfonia di Gravità con Infusione Temporale | 84 | 3.462 | 24.26 | 6 | 14.0 |
| Viaggio Galattico: Sinfonia dei Sensi | 75 | 3.126 | 23.99 | 8 | 9.38 |
| Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plas | 95 | 4.049 | 23.46 | 5 | 19.0 |
| Sinfonia Quantica dell'Oceano Interstellare | 94 | 4.007 | 23.46 | 6 | 15.67 |
| Cosmic Synchrony: Il Destino di Pulsar | 72 | 3.168 | 22.73 | 6 | 12.0 |
| Sinfonia del Multiverso Nascente | 84 | 3.797 | 22.12 | 6 | 14.0 |
| Sinfonia del Multiverso Calante | 85 | 3.965 | 21.44 | 5 | 17.0 |
| L'Estasi Cosmica di Nova | 63 | 3.084 | 20.43 | 7 | 9.0 |
| Sinfonia Temporale del Drago | 82 | 4.133 | 19.84 | 7 | 11.71 |
| Sinfonia Celestiale di Gnocchi del Crepuscolo | 88 | 4.469 | 19.69 | 6 | 14.67 |
| Universo Cosmico nel Piatto | 73 | 3.713 | 19.66 | 8 | 9.12 |
| Più-dimensionale Sinfonia di Sapori: La Carne del Cosmo | 95 | 4.846 | 19.6 | 6 | 15.83 |
| Nebulosa Celestiale di Sogni Quantici | 71 | 3.671 | 19.34 | 8 | 8.88 |
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sf | 100 | 5.224 | 19.14 | 5 | 20.0 |
| Galassia di Sapore | 61 | 3.252 | 18.76 | 8 | 7.62 |
| Antipasto Stellare dell'Eterna Armonia | 72 | 3.839 | 18.75 | 8 | 9.0 |
| Galassia di Sapore Interstellare | 94 | 5.056 | 18.59 | 10 | 9.4 |
| Cosmic Serenade | 65 | 3.545 | 18.34 | 7 | 9.29 |
| Plasma Celestiale al Risotto di Kraken nell'Aura del Sole | 88 | 4.888 | 18.0 | 7 | 12.57 |
| Risotto Interdimensionale alla Carne di Drago e Balena Spaziale con Biscotti del | 88 | 4.930 | 17.85 | 8 | 11.0 |
| Sinfonia Cosmica del Multiverso | 100 | 5.643 | 17.72 | 7 | 14.29 |
| Universo in Fusilli - Variazione Celestiale | 62 | 3.503 | 17.7 | 5 | 12.4 |
| Sinfonia Cosmica in Otto Movimenti | 90 | 5.182 | 17.37 | 8 | 11.25 |
| Universo in Un Boccone | 62 | 3.629 | 17.08 | 9 | 6.89 |
| La Creazione di Nova | 58 | 3.420 | 16.96 | 8 | 7.25 |
| Sinfonia Cosmica di Armonie Terrestri e Celesti | 90 | 5.350 | 16.82 | 7 | 12.86 |
| Sinfonia Cosmica di Mare e Stelle | 77 | 4.594 | 16.76 | 5 | 15.4 |
| Sinfonia di Multiverso: La Danza degli Elementi | 90 | 5.559 | 16.19 | 5 | 18.0 |
| Sinfonia Cosmica: Versione Data | 84 | 5.266 | 15.95 | 6 | 14.0 |
| Sinfonia Cosmica di Luminiscenze e Contrasti | 81 | 5.140 | 15.76 | 7 | 11.57 |
| Sinfonia Cosmica: Versione Pizza | 79 | 5.014 | 15.76 | 9 | 8.78 |
| Sinfonia Cosmica di Sapore | 80 | 5.098 | 15.69 | 7 | 11.43 |
| Armonia Cosmica alla Tavola d'Oro | 68 | 4.343 | 15.66 | 5 | 13.6 |
| Ecosistema Celeste | 56 | 3.587 | 15.61 | 6 | 9.33 |
| Il Viaggio Celeste | 49 | 3.336 | 14.69 | 8 | 6.12 |
| Il Crepuscolo dell’Unicorno | 47 | 3.210 | 14.64 | 5 | 9.4 |
| Sinfonia del Multiverso | 80 | 5.517 | 14.5 | 5 | 16.0 |
| Il Risveglio della Fenice sull'Arcobaleno d'Oceano | 47 | 3.294 | 14.27 | 8 | 5.88 |
| Odissea Temporale | 60 | 4.259 | 14.09 | 7 | 8.57 |
| Sinfonia di Stagioni Stellari | 85 | 6.063 | 14.02 | 9 | 9.44 |
| Sinfonia di Cristalli e Rigenerazione | 75 | 5.434 | 13.8 | 8 | 9.38 |
| Sinfonia Temporale al Tocco di Crono | 85 | 6.231 | 13.64 | 10 | 8.5 |
| Sinfonia Aromatica del Multiverso | 89 | 6.650 | 13.38 | 5 | 17.8 |
| Il Viaggio delle Dimensioni Confluenti | 55 | 4.175 | 13.17 | 9 | 6.11 |
| Sinfonia di Crepuscolo Celestiale | 79 | 6.021 | 13.12 | 6 | 13.17 |
| Galassie Infiammate: Sinfonia Cosmica in Sei Dimensioni | 95 | 7.280 | 13.05 | 8 | 11.88 |
| Viaggio Celeste nel Multiverso | 74 | 5.685 | 13.02 | 7 | 10.57 |
| Viaggio Cosmico nel Multiverso | 89 | 6.860 | 12.97 | 5 | 17.8 |
| Delizia Astrale all'Essenza del Multiverso | 82 | 6.357 | 12.9 | 9 | 9.11 |
| Sinfonia Temporale nello Spaghi del Sole | 77 | 5.979 | 12.88 | 6 | 12.83 |
| Risotto Cosmico Multiversale | 60 | 4.678 | 12.83 | 5 | 12.0 |
| Sinfonia Cosmologica | 68 | 5.308 | 12.81 | 5 | 13.6 |
| Galassia Speculare | 48 | 3.755 | 12.78 | 7 | 6.86 |
| Nebulose Pensanti: Sinfonia del Multiverso | 90 | 7.070 | 12.73 | 9 | 10.0 |
| Nebulosa Celestiale alla Stellaris | 90 | 7.112 | 12.65 | 9 | 10.0 |
| Sinfonia Galattica ai Cristalli di Nebulite | 73 | 5.811 | 12.56 | 6 | 12.17 |
| Portale del Cosmo: Sinfonia di Sapori Multidimensionali | 72 | 5.769 | 12.48 | 5 | 14.4 |
| Sinfonia Cosmica di Terracotta | 85 | 6.818 | 12.47 | 5 | 17.0 |
| Galassie Riflesse: Sinfonia del Multiverso | 83 | 6.776 | 12.25 | 11 | 7.55 |
| Nebulosa di Fenice con Sinfonia Eterea | 75 | 6.189 | 12.12 | 5 | 15.0 |
| Sinfonia Interstellare di Fusilli del Vento con Nettare di Sirena | 79 | 6.524 | 12.11 | 6 | 13.17 |
| Il Viaggio dell'Etereo Risveglio | 55 | 4.552 | 12.08 | 9 | 6.11 |
| Sinfonia del Cosmo e della Leggenda | 57 | 4.762 | 11.97 | 5 | 11.4 |
| Luce e Ombra di Nomea Spaziale | 40 | 3.378 | 11.84 | 6 | 6.67 |
| Sinfonia di Gusti del Multiverso | 67 | 5.727 | 11.7 | 6 | 11.17 |
| Cosmos Quantum Fusion | 55 | 4.804 | 11.45 | 5 | 11.0 |
| Echi del Mare Eterno | 47 | 4.217 | 11.15 | 5 | 9.4 |
| Sinfonia del Cosmo Rigenerante | 70 | 6.315 | 11.08 | 6 | 11.67 |
| Sinfonia Cosmica ma Fatta Bene | 82 | 7.406 | 11.07 | 6 | 13.67 |
| Viaggio dei Sensi: Bolla Temporale di Aromi Ancestrali | 67 | 6.105 | 10.97 | 5 | 13.4 |
| Melodia del Multiverso Parallelo | 70 | 6.399 | 10.94 | 9 | 7.78 |
| Sinfonia Tempolare Galattica | 64 | 5.853 | 10.93 | 11 | 5.82 |
| Pane e Carne Rivisitato | 50 | 4.636 | 10.79 | 10 | 5.0 |
| Galassie in Epifania: Risotto Celestiale con Preziosi dell'Universo | 97 | 9.084 | 10.68 | 9 | 10.78 |
| Ode al Crepuscolo del Multiverso | 69 | 6.483 | 10.64 | 7 | 9.86 |
| Sinfonia Celestiale | 89 | 8.371 | 10.63 | 8 | 11.12 |
| Galassia Commovente di Stellari | 79 | 7.490 | 10.55 | 8 | 9.88 |
| Nebulosa Galattica | 31 | 3.000 | 10.33 | 5 | 6.2 |
| Echi del Cosmo | 45 | 4.385 | 10.26 | 6 | 7.5 |
| Rintocchi del Cosmo | 44 | 4.301 | 10.23 | 5 | 8.8 |
| Galassia a Tavola: Sinfonia di Tempeste Cosmiche | 82 | 8.035 | 10.21 | 6 | 13.67 |
| Armonia Cosmica della Fenice | 78 | 7.699 | 10.13 | 6 | 13.0 |
| Alternate Realities Risotto | 50 | 4.972 | 10.06 | 7 | 7.14 |
| Sinfonia Cosmica: La Danza dell'Universo | 96 | 9.545 | 10.06 | 8 | 12.0 |
| Sinfonia Astrale - Risotto Multiversale con Risacca Celeste | 100 | 9.965 | 10.04 | 9 | 11.11 |
| Il Risveglio del Multiverso | 47 | 4.720 | 9.96 | 5 | 9.4 |
| Risveglio Cosmico: Una Sinfonia di Sapori Universali | 92 | 9.252 | 9.94 | 8 | 11.5 |
| Ethereal Temporal Elixir | 44 | 4.427 | 9.94 | 8 | 5.5 |
| Nebulare Asteroideo con Crepuscolo di Mucca | 40 | 4.091 | 9.78 | 11 | 3.64 |
| Sinfonia Celeste dell'Equilibrio Temporale | 92 | 9.420 | 9.77 | 6 | 15.33 |
| Sinfonia Galattica alla Griglia Cangiante | 70 | 7.238 | 9.67 | 6 | 11.67 |
| Sinfonia Cosmica di Sapori | 81 | 8.413 | 9.63 | 8 | 10.12 |
| Portale Interdimensionale di Sapori | 62 | 6.441 | 9.63 | 6 | 10.33 |
| Euforia Cosmica | 64 | 6.734 | 9.5 | 7 | 9.14 |
| Cosmopolis delle Galassie Perdute | 55 | 5.895 | 9.33 | 8 | 6.88 |
| Essenze dell'Infinito | 36 | 3.881 | 9.28 | 5 | 7.2 |
| Sinfonia Cosmica di Andromeda | 85 | 9.210 | 9.23 | 5 | 17.0 |
| Galassia di Sapore Quantum | 72 | 7.825 | 9.2 | 5 | 14.4 |
| Serenata del Multiverso | 60 | 6.692 | 8.97 | 6 | 10.0 |
| Sinfonia Cosmica ma Fatta Male | 64 | 7.154 | 8.95 | 7 | 9.14 |
| Galassia nel Piatto: Sinfonia di Sapori e Dimensioni | 87 | 9.839 | 8.84 | 6 | 14.5 |
| Sfogliare Galattico di Sogni Temporali | 54 | 6.147 | 8.78 | 6 | 9.0 |
| Galassia di Celestial Delight | 71 | 8.161 | 8.7 | 6 | 11.83 |
| Nebulose della Fenice su Vento Lunare | 61 | 7.028 | 8.68 | 7 | 8.71 |
| Sinfonia Cosmica | 85 | 10.091 | 8.42 | 9 | 9.44 |
| Portale del Cosmo: Sinfonia di Sapori e Tempi | 75 | 8.916 | 8.41 | 10 | 7.5 |
| Sinfonia Celestiale di Echi Galattici | 77 | 9.336 | 8.25 | 5 | 15.4 |
| Galassie Sospese: Un Viaggio di Sapori Cosmogalattici | 60 | 7.322 | 8.19 | 6 | 10.0 |
| Sinfonia Astrale | 82 | 10.175 | 8.06 | 7 | 11.71 |
| Creazione Celestiale: L'Alba del Cosmo | 66 | 8.245 | 8.0 | 7 | 9.43 |
| Galassia Incantata: Un Viaggio Attraverso l'Infinito | 74 | 9.294 | 7.96 | 8 | 9.25 |
| Galassia di Sapori Interstellari | 82 | 10.343 | 7.93 | 9 | 9.11 |
| Piastrella Celestiale di Gnocchi del Crepuscolo con Nebulosa di Riso di Cassandr | 86 | 10.846 | 7.93 | 5 | 17.2 |
| Galassia Risvegliata | 47 | 5.937 | 7.92 | 6 | 7.83 |
| Risveglio Cosmico | 77 | 9.755 | 7.89 | 7 | 11.0 |
| Più Lontano delle Stelle | 44 | 5.601 | 7.86 | 5 | 8.8 |
| La Balena incontra la Mandragora | 60 | 7.657 | 7.84 | 7 | 8.57 |
| Sinfonia di Galassie Riflesse | 67 | 8.580 | 7.81 | 7 | 9.57 |
| Viaggio Gastronomico tra le Stelle | 49 | 6.273 | 7.81 | 5 | 9.8 |
| Sinfonia degli Elementi Eterni | 70 | 9.042 | 7.74 | 9 | 7.78 |
| Galassia Infinita: Viaggio tra Memorie e Stelle | 67 | 8.664 | 7.73 | 6 | 11.17 |
| Danza Luminosa del Multiverso | 53 | 6.944 | 7.63 | 5 | 10.6 |
| Pioggia di Andromeda | 56 | 7.364 | 7.6 | 9 | 6.22 |
| Eterna Sinfonia del Cosmo | 66 | 8.706 | 7.58 | 7 | 9.43 |
| Nebulose a Strati | 50 | 6.608 | 7.57 | 9 | 5.56 |
| Pioggia Calante dell'Universo | 62 | 8.203 | 7.56 | 7 | 8.86 |
| Sinfonia Cosmica di Aurora | 66 | 8.748 | 7.54 | 5 | 13.2 |
| Valzer Cosmico di Asteria | 65 | 8.622 | 7.54 | 6 | 10.83 |
| Quadrifonia Cosmica: Sinfonia di Sapori e Dimensioni | 95 | 12.650 | 7.51 | 10 | 9.5 |
| Sinfonia Cosmica della Rinascita | 78 | 10.510 | 7.42 | 9 | 8.67 |
| Sinfonia del Multiverso di Gusto | 74 | 10.049 | 7.36 | 7 | 10.57 |
| Stella Nova | 40 | 5.476 | 7.3 | 8 | 5.0 |
| Sinfonia Temporale Galattica | 73 | 10.007 | 7.29 | 6 | 12.17 |
| Viaggio Cosmico tra Mare e Stelle | 78 | 10.720 | 7.28 | 7 | 11.14 |
| Crescendo Cosmico | 64 | 8.832 | 7.25 | 7 | 9.14 |
| Galassia Suprema | 66 | 9.126 | 7.23 | 7 | 9.43 |
| Rivisitazione del Kraken sotto Molecole | 60 | 8.329 | 7.2 | 8 | 7.5 |
| Microcosmo in un Boccone | 50 | 6.986 | 7.16 | 10 | 5.0 |
| Etereo Crepuscolare | 28 | 3.923 | 7.14 | 5 | 5.6 |
| Galassia nel Piatto: Sinfonia Universale di Aromi e Sapori | 83 | 11.685 | 7.1 | 9 | 9.22 |
| Galassia Riflessa | 56 | 7.909 | 7.08 | 7 | 8.0 |
| Sinfonia Cosmica: il Ritorno dell'Imperatore | 82 | 11.601 | 7.07 | 5 | 16.4 |
| Sinfonia di Galassie Perdute | 63 | 9.000 | 7.0 | 5 | 12.6 |
| Galassia di Sapori: L'Eterno Ritorno | 71 | 10.427 | 6.81 | 10 | 7.1 |
| Cosmic Harmony Risotto | 55 | 8.119 | 6.77 | 5 | 11.0 |
| Fusione Celeste | 62 | 9.168 | 6.76 | 10 | 6.2 |
| Galassia di Sapori: Sinfonia Transdimensionale | 80 | 11.853 | 6.75 | 5 | 16.0 |
| Sinfonia Celestiale dei Ricordi | 81 | 12.189 | 6.65 | 8 | 10.12 |
| Odissea Cosmica di Nettuno | 49 | 7.448 | 6.58 | 5 | 9.8 |
| Enigma Celeste | 52 | 7.951 | 6.54 | 5 | 10.4 |
| Sinfonia dell'Universo Morente | 75 | 11.476 | 6.54 | 7 | 10.71 |
| Eclissi Armonica di Sapori | 29 | 4.510 | 6.43 | 7 | 4.14 |
| Sinfonia Celeste di Granuli Arcobaleno e Riso di Cassandra | 70 | 10.888 | 6.43 | 5 | 14.0 |
| Nebulosa di Dragone all'Essenza di Vuoto | 69 | 10.762 | 6.41 | 5 | 13.8 |
| Tris di Carne con Pane | 50 | 7.867 | 6.36 | 9 | 5.56 |
| Galassia Aurorale | 66 | 10.385 | 6.36 | 11 | 6.0 |
| Sinfonia Cosmica: la Vendetta Fantasma | 73 | 11.517 | 6.34 | 5 | 14.6 |
| Cosmo Sferico di Sogni Rigenerativi | 34 | 5.392 | 6.31 | 7 | 4.86 |
| Il Risveglio del Drago Celeste | 70 | 11.140 | 6.28 | 9 | 7.78 |
| Interstellar Requiem | 60 | 9.587 | 6.26 | 5 | 12.0 |
| Rivelazione del Multiverso | 65 | 10.469 | 6.21 | 7 | 9.29 |
| Galassia di Sogni Cosmogastronomici | 52 | 8.455 | 6.15 | 6 | 8.67 |
| Sinfonia Cosmica all'Alba di Fenice | 85 | 13.867 | 6.13 | 6 | 14.17 |
| Portale Cosmico del Kraken | 79 | 12.944 | 6.1 | 10 | 7.9 |
| Interstellare Risveglio di Kraken | 90 | 14.832 | 6.07 | 8 | 11.25 |
| Cosmos Risotto Reale | 46 | 7.615 | 6.04 | 6 | 7.67 |
| Eclissi del Drago nell'Abbraccio del Kraken | 66 | 10.972 | 6.02 | 6 | 11.0 |
| Sinfonia Cosmica: Il Crescendo delle Stelle | 84 | 13.951 | 6.02 | 10 | 8.4 |
| Risveglio Cosmico: Un Viaggio nel Sapore Quantistico | 76 | 12.776 | 5.95 | 6 | 12.67 |
| La Sinfonia dell'Universo | 68 | 11.434 | 5.95 | 8 | 8.5 |
| Sinfonia Quantistica dell'Universo | 87 | 14.664 | 5.93 | 9 | 9.67 |
| Universo Incantato: Sinfonia dei Gusti Cosmogonici | 67 | 11.308 | 5.93 | 6 | 11.17 |
| Danza Cosmica al Crepuscolo | 60 | 10.133 | 5.92 | 5 | 12.0 |
| Cosmic Rhapsody | 49 | 8.287 | 5.91 | 5 | 9.8 |
| Simfonia Celeste di Aurora | 52 | 8.874 | 5.86 | 7 | 7.43 |
| Sinfonia dei Ricordi Celesti | 70 | 11.937 | 5.86 | 5 | 14.0 |
| Valzer delle Stelle | 50 | 8.538 | 5.86 | 9 | 5.56 |
| Portale Astrale di Sapori | 47 | 8.077 | 5.82 | 6 | 7.83 |
| Sinfonia Galattica di Sapori con Sorpresa di Drago Fiammante | 68 | 11.727 | 5.8 | 6 | 11.33 |
| Pizza Cosmica all'Essenza di Drago con Nebbia Arcobaleno e Funghi Orbitali | 83 | 14.371 | 5.78 | 10 | 8.3 |
| Concordanza Cosmica | 65 | 11.266 | 5.77 | 8 | 8.12 |
| Il Viaggio Cosmico di Marinetti | 62 | 10.804 | 5.74 | 6 | 10.33 |
| Risotto dei Multiversi | 43 | 7.531 | 5.71 | 5 | 8.6 |
| Cosmic Harmony Infusion | 64 | 11.224 | 5.7 | 7 | 9.14 |
| Universo in Fluttuazione | 56 | 9.923 | 5.64 | 6 | 9.33 |
| Sinfonia Temporale delle Profondità Infrasoniche | 83 | 14.874 | 5.58 | 5 | 16.6 |
| Nebulosa dell'Infinito: Un Viaggio attraverso il Cosmo del Gusto | 54 | 9.671 | 5.58 | 10 | 5.4 |
| Evanescenza Cosmica | 65 | 11.643 | 5.58 | 7 | 9.29 |
| Astro-Risotto alle Onde Temporali | 40 | 7.196 | 5.56 | 5 | 8.0 |
| Sinfonia dell'Infinito: Un Viaggio Gnodale tra Terra e Universi | 80 | 14.497 | 5.52 | 6 | 13.33 |
| Nebulosa di Drago Interdimensionale | 52 | 9.503 | 5.47 | 5 | 10.4 |
| Aurora del Cosmo | 53 | 9.797 | 5.41 | 6 | 8.83 |
| Viaggio dei Ricordi Stellari | 65 | 12.105 | 5.37 | 7 | 9.29 |
| La Voce del Vento | 35 | 6.566 | 5.33 | 5 | 7.0 |
| Porta Celestiale alle Stelle | 50 | 9.378 | 5.33 | 6 | 8.33 |
| Panetto di Carne | 40 | 7.573 | 5.28 | 8 | 5.0 |
| Galassia d'Aromi Perduti | 42 | 7.993 | 5.25 | 5 | 8.4 |
| Sogni di Abisso Cosmico | 56 | 10.678 | 5.24 | 7 | 8.0 |
| Risotto Cosmico alla Draconia | 68 | 13.028 | 5.22 | 9 | 7.56 |
| Antipasto Celestiale | 60 | 11.559 | 5.19 | 8 | 7.5 |
| Nebulosa Eterna | 50 | 9.713 | 5.15 | 9 | 5.56 |
| Sinfonia Quantistica delle Stelle | 75 | 14.622 | 5.13 | 8 | 9.38 |
| Sinfonia Cosmica di Terre e Stelle | 65 | 12.692 | 5.12 | 6 | 10.83 |
| Galassia di Sapore Interdimensionale | 60 | 11.811 | 5.08 | 6 | 10.0 |
| Galassia di Sapori Eterei | 56 | 11.098 | 5.05 | 7 | 8.0 |
| Sinfonia Crepuscolare | 61 | 12.147 | 5.02 | 5 | 12.2 |
| Sinfonia Galattica Agentica | 55 | 11.056 | 4.97 | 5 | 11.0 |
| Dimensioni del Mare Stellato | 34 | 6.902 | 4.93 | 5 | 6.8 |
| Sinfonia Multiversale in Otto Movimenti | 56 | 11.392 | 4.92 | 7 | 8.0 |
| La Mucca Che Stordisce l'Universo | 66 | 13.406 | 4.92 | 7 | 9.43 |
| Il Rapsodo Celestiale | 70 | 14.245 | 4.91 | 9 | 7.78 |
| Odissea Celestiale | 69 | 14.077 | 4.9 | 8 | 8.62 |
| Galassia in Tavola: Sinfonia dei Sensi | 65 | 13.322 | 4.88 | 5 | 13.0 |
| Fenice sull'Orizzonte degli Eventi | 63 | 12.902 | 4.88 | 9 | 7.0 |
| Cosmos Culinary Symphony | 50 | 10.259 | 4.87 | 10 | 5.0 |
| Falso Risotto dell'Infinito Multiverso | 71 | 14.580 | 4.87 | 7 | 10.14 |
| Una Mucca e una Balena nella Singolarità | 63 | 12.986 | 4.85 | 10 | 6.3 |
| Portale delle Meraviglie | 50 | 10.301 | 4.85 | 10 | 5.0 |
| Galassie alla Spirale di Vento con Sfera di Ghiaccio Eterno | 64 | 13.364 | 4.79 | 9 | 7.11 |
| Nebulosa Celeste di Terrafirma | 47 | 9.881 | 4.76 | 6 | 7.83 |
| Cosmic Symphony di Ghiaccio e Fuoco | 66 | 14.035 | 4.7 | 6 | 11.0 |
| Portale delle Stelle | 49 | 10.636 | 4.61 | 5 | 9.8 |
| Galassia Ardente | 62 | 13.657 | 4.54 | 9 | 6.89 |
| Sinfonia Cosmica alla Szechuan | 63 | 13.909 | 4.53 | 6 | 10.5 |
| Fenice Galattica | 35 | 7.741 | 4.52 | 6 | 5.83 |
| Galassia di Fusilli Sferici alla Risonanza Crononica | 59 | 13.070 | 4.51 | 8 | 7.38 |
| Rapsodia Quantistica nel Cosmo | 35 | 7.783 | 4.5 | 5 | 7.0 |
| Entropia Eterna | 38 | 8.497 | 4.47 | 6 | 6.33 |
| Galassia di Cosmo-Delizie | 61 | 13.699 | 4.45 | 6 | 10.17 |
| Sinfonia Quantica Galattica | 49 | 11.014 | 4.45 | 5 | 9.8 |
| Galassia di Sapori di Aurora | 52 | 11.769 | 4.42 | 6 | 8.67 |
| Mandragola e Radici | 58 | 13.154 | 4.41 | 5 | 11.6 |
| Stellar Fusion | 46 | 10.594 | 4.34 | 5 | 9.2 |
| Cosmic Harmony | 57 | 13.238 | 4.31 | 5 | 11.4 |
| Mycoflora con Polvere di Stelle Sbagliato | 62 | 14.413 | 4.3 | 5 | 12.4 |
| Cosmofantasia di Terra e Mare nel Vortice delle Stelle | 60 | 13.993 | 4.29 | 9 | 6.67 |
| Sinfonia del Cosmo | 51 | 11.979 | 4.26 | 5 | 10.2 |
| Galassia di Sapore Quantico | 62 | 14.790 | 4.19 | 7 | 8.86 |
| Galassia di Sapori | 44 | 10.552 | 4.17 | 5 | 8.8 |
| Rinascita Cosmica | 59 | 14.203 | 4.15 | 8 | 7.38 |
| Eclissi Quantica: Viaggio nei Reami del Gusto | 47 | 11.350 | 4.14 | 10 | 4.7 |
| Bistecca Cacofonica dell'Infinito | 59 | 14.287 | 4.13 | 8 | 7.38 |
| Il Ricordo del Fuoco Celeste | 49 | 11.895 | 4.12 | 7 | 7.0 |
| Ode Cosmica di Terra e Stelle | 60 | 14.958 | 4.01 | 8 | 7.5 |
| Pizza Cri | 50 | 12.483 | 4.01 | 10 | 5.0 |
| Tris di Verdure con Xenodonte | 58 | 14.538 | 3.99 | 8 | 7.25 |
| Galassia Sensoriale | 55 | 13.783 | 3.99 | 6 | 9.17 |
| Pizza Baby Daniele | 50 | 12.524 | 3.99 | 10 | 5.0 |
| Il Simposio degli Infiniti Ricordi | 48 | 12.063 | 3.98 | 8 | 6.0 |
| Pizza Baby Lorenzo | 50 | 12.566 | 3.98 | 10 | 5.0 |
| Galaxia Gustativa | 35 | 8.790 | 3.98 | 5 | 7.0 |
| Pizza Baby Simone e Alessandro | 50 | 12.608 | 3.97 | 9 | 5.56 |
| Il Risveglio delle Stelle | 37 | 9.462 | 3.91 | 6 | 6.17 |
| Portale di Sapori Arcani | 50 | 12.860 | 3.89 | 5 | 10.0 |
| Piccola Odissea Cosmica | 52 | 13.448 | 3.87 | 6 | 8.67 |
| Lumière Cosmica | 49 | 12.734 | 3.85 | 5 | 9.8 |
| L'Unicorno piange il Kraken | 52 | 13.490 | 3.85 | 8 | 6.5 |
| Galassia di Sapori: Il Viaggio Senza Tempo | 55 | 14.329 | 3.84 | 9 | 6.11 |
| Cosmos in Tavola | 42 | 10.930 | 3.84 | 7 | 6.0 |
| Nebulae Di-Cedri Risvegliati | 37 | 9.629 | 3.84 | 7 | 5.29 |
| Rapsodia dei Ricordi Celesti | 46 | 12.021 | 3.83 | 7 | 6.57 |
| Galassia Rinascente | 50 | 13.112 | 3.81 | 7 | 7.14 |
| Pizza Fra | 46 | 12.273 | 3.75 | 8 | 5.75 |
| Pioggia di Dimensioni Galattiche | 55 | 14.916 | 3.69 | 6 | 9.17 |
| L'Ascensione Siderale | 47 | 12.818 | 3.67 | 8 | 5.88 |
| Nebulosa di Confini Sfondati | 50 | 13.741 | 3.64 | 8 | 6.25 |
| Pizza Gio | 44 | 12.315 | 3.57 | 6 | 7.33 |
| Pizza Raul | 44 | 12.441 | 3.54 | 6 | 7.33 |
| Galassia di Sapori Sublimi | 52 | 14.748 | 3.53 | 6 | 8.67 |
| Pizza Emma | 43 | 12.357 | 3.48 | 6 | 7.17 |
| Sinfonia Galattica | 52 | 15.000 | 3.47 | 7 | 7.43 |
| Evanescenza Quantica | 50 | 14.706 | 3.4 | 7 | 7.14 |
| Nebulosa di Sapori dell'Infinito | 49 | 14.455 | 3.39 | 5 | 9.8 |
| Verso l'Inedito Oltre | 30 | 8.958 | 3.35 | 6 | 5.0 |
| Galaxia Rinasciata | 44 | 13.196 | 3.33 | 5 | 8.8 |
| La Balena Sputafuoco | 45 | 13.573 | 3.32 | 5 | 9.0 |
| Sfere del Ricordo Astrale | 39 | 12.231 | 3.19 | 6 | 6.5 |
| L'Abbraccio del Cosmo | 35 | 11.182 | 3.13 | 5 | 7.0 |
| Cosmopastico di Meraviglie Celesti | 42 | 13.825 | 3.04 | 7 | 6.0 |
| L'Eternità al Crepuscolo | 36 | 13.531 | 2.66 | 7 | 5.14 |
| Sassi e Sassolini | 36 | 13.615 | 2.64 | 6 | 6.0 |
| Nebulosa di Sapori Quantici | 34 | 13.280 | 2.56 | 5 | 6.8 |
| Il Banchetto delle Galassie | 32 | 14.119 | 2.27 | 8 | 4.0 |
| Cosmologia Terrestre: Viaggio in Otto Dimensioni | 32 | 14.161 | 2.26 | 5 | 6.4 |
| Dimensioni di Sapori Infusi | 23 | 10.217 | 2.25 | 6 | 3.83 |
| Pizza Luca | 23 | 12.399 | 1.85 | 6 | 3.83 |

## 16 — Pairplot / Joint Distribution Summary

The pairplot visualises pairwise scatter + KDE for the 3 numeric variables.

### Full Descriptive Statistics

|       |   prestige |   prep_s |   n_ingredients |
|:------|-----------:|---------:|----------------:|
| count |    287     |  287     |         287     |
| mean  |     62.774 |    9     |           6.861 |
| std   |     16.915 |    3.482 |           1.631 |
| min   |     23     |    3     |           5     |
| 25%   |     50     |    6     |           5     |
| 50%   |     62     |    9     |           7     |
| 75%   |     75     |   12     |           8     |
| max   |    100     |   15     |          11     |

### Pearson Correlations (repeated for completeness)

|               |   Prestige |   Prep Time (s) |   # Ingredients |
|:--------------|-----------:|----------------:|----------------:|
| Prestige      |     1      |         -0.1224 |          0.1704 |
| Prep Time (s) |    -0.1224 |          1      |          0.0983 |
| # Ingredients |     0.1704 |          0.0983 |          1      |

### Spearman Correlations

|               |   Prestige |   Prep Time (s) |   # Ingredients |
|:--------------|-----------:|----------------:|----------------:|
| Prestige      |     1      |          -0.116 |          0.1719 |
| Prep Time (s) |    -0.116  |           1     |          0.104  |
| # Ingredients |     0.1719 |           0.104 |          1      |

