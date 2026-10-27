"""Transfermarkt position names (as in the dataset dump) mapped to lineup roles and pt-BR labels."""

POSITION_ROLES: dict[str, str] = {
    'Goalkeeper': 'GK',
    'Centre-Back': 'CB',
    'Left-Back': 'LB',
    'Right-Back': 'RB',
    'Defensive Midfield': 'DM',
    'Central Midfield': 'CM',
    'Right Midfield': 'CM',
    'Left Midfield': 'CM',
    'Attacking Midfield': 'AM',
    'Centre-Forward': 'ST',
    'Second Striker': 'ST',
    'Left Winger': 'LW',
    'Right Winger': 'RW',
}

POSITION_LABELS: dict[str, str] = {
    'Goalkeeper': 'Goleiro',
    'Centre-Back': 'Zagueiro',
    'Left-Back': 'Lateral-Esquerdo',
    'Right-Back': 'Lateral-Direito',
    'Defensive Midfield': 'Volante',
    'Central Midfield': 'Meia Central',
    'Left Midfield': 'Meia-Esquerda',
    'Right Midfield': 'Meia-Direita',
    'Attacking Midfield': 'Meia Ofensivo',
    'Left Winger': 'Ponta Esquerda',
    'Right Winger': 'Ponta Direita',
    'Second Striker': 'Segundo Atacante',
    'Centre-Forward': 'Centroavante',
}

FOOT_LABELS: dict[str, str] = {
    'left': 'Esquerdo',
    'right': 'Direito',
    'both': 'Ambidestro',
}
