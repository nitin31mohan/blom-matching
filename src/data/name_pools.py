"""Diverse first and last name pools for synthetic data generation.

Covers multiple cultural backgrounds reflecting Blom Social's London-based
user base. These names are used only for synthetic/demo data — never real.
"""

FIRST_NAMES = [
    # English / Western European
    "Alice", "Ben", "Charlotte", "David", "Emma", "Finn", "Grace", "Harry",
    "Isla", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Patrick",
    "Rachel", "Sam", "Tara", "Will", "Zoe", "Alex", "Beth", "Chris",
    "Diana", "Edward", "Fiona", "George", "Hannah", "Ian", "Jessica",
    "Kevin", "Laura", "Mark", "Natalie", "Oscar", "Penny", "Quinn",
    "Rose", "Simon", "Tina", "Uma", "Victor", "Wendy", "Xavier", "Yasmin",
    # Irish
    "Aoife", "Ciarán", "Clodagh", "Conor", "Deirdre", "Eoin", "Fionnuala",
    "Niamh", "Oisín", "Rónán", "Seán", "Siobhán",
    # French
    "Amélie", "Baptiste", "Camille", "Élodie", "Florent", "Gaëlle",
    "Hugo", "Inès", "Julien", "Léa", "Mathieu", "Nathalie",
    # German
    "Anna", "Björn", "Clara", "Dieter", "Elke", "Frank", "Greta",
    "Heinz", "Inge", "Jonas", "Karin", "Lars", "Monika",
    # South Asian (Indian / Pakistani / Sri Lankan)
    "Aarav", "Ananya", "Arjun", "Deepa", "Divya", "Farhan", "Ishaan",
    "Kavya", "Kiran", "Meera", "Naveen", "Neha", "Parveen", "Priya",
    "Rahul", "Riya", "Rohan", "Saanvi", "Sana", "Sanjay", "Shilpa",
    "Suresh", "Trisha", "Uday", "Vandana", "Vikram", "Aisha", "Bilal",
    "Fatima", "Hassan", "Imran", "Layla", "Maryam", "Omar", "Yasmin",
    "Zainab", "Zara",
    # East Asian (Chinese / Japanese / Korean)
    "Aiko", "Chen Wei", "Hana", "Hiroshi", "Ji-ho", "Jun", "Li Na",
    "Mei", "Min-jun", "Seo-yeon", "Sora", "Taro", "Wei", "Yuki",
    "Zhang Wei", "Ling", "Ryo", "Sakura",
    # African / Caribbean
    "Adaeze", "Amara", "Chidi", "Chioma", "Dami", "Emeka", "Funmi",
    "Ibironke", "Ifeanyi", "Kelechi", "Nkechi", "Ola", "Seun", "Temi",
    "Tobi", "Uche", "Yetunde", "Abena", "Ama", "Kofi", "Kwame", "Nana",
    "Ayana", "Destiny", "Jahmal", "Kezia", "Naomi", "Tanesha",
    # Middle Eastern / North African
    "Ahmad", "Amira", "Dina", "Hamid", "Karima", "Khalid", "Leila",
    "Malik", "Nadia", "Rania", "Samir", "Tariq", "Youssef",
    # Eastern European
    "Aleksei", "Anastasia", "Bogdan", "Daria", "Dmitri", "Elena",
    "Ivan", "Kateryna", "Marta", "Natasha", "Olga", "Petro", "Tatiana",
    # Spanish / Latin American
    "Adriana", "Alejandro", "Catalina", "Diego", "Elena", "Fernando",
    "Gabriela", "Ignacio", "Lucía", "Miguel", "Pablo", "Sofia",
    # Scandinavian
    "Astrid", "Erik", "Freya", "Gunnar", "Helena", "Johan", "Kristin",
    "Magnus", "Signe", "Sven", "Thea", "Torsten",
    # Jewish / Hebrew names
    "Ariel", "Dahlia", "Elan", "Ilana", "Lev", "Miriam", "Noam",
    "Rivka", "Shira", "Yael",
]

LAST_NAMES = [
    # English / British
    "Adams", "Baker", "Brown", "Campbell", "Clarke", "Davies", "Evans",
    "Fletcher", "Green", "Harris", "Hughes", "Jackson", "Johnson", "Jones",
    "King", "Lewis", "Martin", "Moore", "Morgan", "Murphy", "O'Brien",
    "Parker", "Patel", "Phillips", "Robinson", "Scott", "Smith", "Taylor",
    "Thomas", "Thompson", "Turner", "Walker", "White", "Williams", "Wilson",
    "Wood", "Wright", "Young",
    # Irish
    "Brennan", "Burke", "Byrne", "Collins", "Connelly", "Daly", "Doyle",
    "Dunne", "Fitzgerald", "Flynn", "Gallagher", "Kelly", "Kennedy",
    "Lynch", "McCarthy", "McDonagh", "McMahon", "Nolan", "O'Connor",
    "O'Donnell", "O'Neill", "O'Sullivan", "Quinn", "Ryan", "Walsh",
    # French
    "Beaulieu", "Bernard", "Bertrand", "Blanc", "Bonnet", "Bouchard",
    "Chevalier", "Dubois", "Dumont", "Dupont", "Faure", "Fontaine",
    "Garnier", "Girard", "Laurent", "Leclerc", "Lefebvre", "Legrand",
    "Leroy", "Martin", "Mercier", "Michel", "Morel", "Petit", "Richard",
    "Rousseau", "Simon", "Thomas",
    # German
    "Bauer", "Beck", "Berger", "Fischer", "Hoffmann", "Koch", "Krause",
    "Lange", "Meyer", "Müller", "Neumann", "Peters", "Richter", "Schmid",
    "Schmidt", "Schneider", "Schreiber", "Schulz", "Wagner", "Walter",
    "Weber", "Wolf",
    # South Asian
    "Agarwal", "Ahmed", "Ali", "Banerjee", "Bose", "Chakraborty",
    "Chatterjee", "Chaudhary", "Das", "Desai", "Ghosh", "Gupta",
    "Hussain", "Joshi", "Khan", "Kumar", "Mehta", "Mishra", "Nair",
    "Patel", "Pillai", "Rao", "Reddy", "Sharma", "Shah", "Singh",
    "Srivastava", "Verma",
    # East Asian
    "Chan", "Chang", "Chen", "Cheng", "Cheung", "Choi", "Chu", "Huang",
    "Kim", "Lee", "Li", "Lin", "Liu", "Luo", "Ma", "Ng", "Park", "Sato",
    "Suzuki", "Tanaka", "Wang", "Wong", "Wu", "Xu", "Yang", "Yip",
    "Yoshida", "Zhang", "Zhao",
    # African / Nigerian / Ghanaian
    "Abiodun", "Adebayo", "Adeyemi", "Afolabi", "Akintola", "Asante",
    "Boateng", "Diallo", "Eze", "Mensah", "Nwosu", "Obi", "Odunsi",
    "Okafor", "Okonkwo", "Osei", "Owusu",
    # Middle Eastern / North African
    "Abdullah", "Al-Farsi", "Amin", "Aziz", "Bakr", "Hassan", "Hossain",
    "Ibrahim", "Ismail", "Khalil", "Mahmoud", "Mansour", "Nasser",
    "Rahman", "Raza", "Siddiqui", "Yilmaz",
    # Eastern European
    "Bondarenko", "Ivanov", "Kovalenko", "Kovalev", "Melnyk", "Morozov",
    "Petrov", "Popov", "Shevchenko", "Sidorov", "Sokolov", "Volkov",
    "Zhuk",
    # Spanish / Portuguese
    "Almeida", "Alvarez", "Costa", "Cruz", "Fernández", "García",
    "Gomes", "González", "Hernández", "López", "Martínez", "Oliveira",
    "Pereira", "Rodrigues", "Sánchez", "Santos", "Silva",
    # Scandinavian
    "Andersen", "Berg", "Dahl", "Eriksen", "Hansen", "Jensen", "Karlsson",
    "Larsen", "Lindqvist", "Nielsen", "Pedersen", "Persson",
    "Svensson", "Thorvaldsen",
    # Jewish surnames
    "Cohen", "Goldberg", "Goldman", "Goldstein", "Katz", "Levi", "Levy",
    "Rosenberg", "Rosenthal", "Shapiro", "Weinberg",
]
