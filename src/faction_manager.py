import json
import os
import logging
import src.utils as utils
from pathlib import Path
import sys
import pandas as pd
import src.game_manager as game_manager

from src.llm.message_thread import message_thread

class Faction:
    def __init__(self, info):
        self.info = info
        self.name = info['name']
        self.names = [ info['name'] ]
        if not isinstance(info['altnames'], float):
            self.names += info['altnames'].split(';')
        self.description = info['description']
        self.factions = info['factions'].split(';')
        if isinstance(info['antifactions'], float):
            self.antifactions = []
        else:
            self.antifactions = info['antifactions'].split(';')

factions: dict[str, Faction] = {}

def sanitize_faction_name(faction : str) -> str:
    def replace_front(haystack : str, needle : str, replacement : str = '') -> str:
        haystack = haystack.strip()
        if haystack.startswith(needle):
            return haystack.replace(needle, replacement, 1).strip()
        return haystack
    # TODO: Remove 'es' and 's' from end of faction name as a poor attempt to convert plural names to singular form
    return replace_front(replace_front(replace_front(replace_front(faction.lower(), "an "), "a "), "member of "), "the ")

def initialize_faction_information(faction_df : pd.DataFrame):
    for index, row in faction_df.iterrows():
        factions[row.loc['name']] = Faction(row)

    factions_initial = list(factions.values())
    factions_keys = list(factions.keys())
    for key in factions_keys:
        faction = factions[key]
        for name in faction.names:
            factions[sanitize_faction_name(name)] = faction
    for faction in factions_initial:
        antifaction_names = list(faction.antifactions)
        faction.antifactions = []
        for antifaction in antifaction_names:
            faction.antifactions += factions[sanitize_faction_name(antifaction)].factions
    logging.info('Successfully initialized faction database.')

def sanitize_form_reference(reference : str):
    formId = ''
    plugin = ''
    if (':' in reference): # Spriggit-style
        stringParts = reference.split(':')
        formId = stringParts[0]
        plugin = stringParts[1]
    elif ('|' in reference): # RobCo Patcher-style
        stringParts = reference.split('|')
        plugin = stringParts[0]
        formId = stringParts[1]
    elif ('~' in reference): # Spell Perk Item Distributor (SPID)-style
        stringParts = reference.split('~')
        formId = stringParts[0]
        plugin = stringParts[1]
    else:
        plugin = 'Skyrim.esm'
        formId = reference
    return f'{int(formId, 16)}:{plugin}'

def add_to_faction(faction_name : str, game_state_manager : game_manager.GameStateManager):
    key = sanitize_faction_name(faction_name)
    if key not in factions.keys():
        logging.info(f'The NPC tried to join the faction "{key}", but the faction isn\'t found.')
        return
    faction = factions[key]
    logging.info(f"The NPC is joining the {faction.name}.")
    game_state_manager.write_game_info(f'_mantella_join_faction', faction.name)
    i = 1
    for faction_formid in faction.factions:
        if len(faction_formid) > 0:
            game_state_manager.write_game_info(f'_mantella_join_faction_{i}', sanitize_form_reference(faction_formid))
            i += 1
    while i < 10:
        game_state_manager.write_game_info(f'_mantella_join_faction_{i}', '')
        i += 1
    i = 1
    for faction_formid in faction.antifactions:
        if len(faction_formid) > 0:
            game_state_manager.write_game_info(f'_mantella_leave_faction_{i}', sanitize_form_reference(faction_formid))
            i += 1
    while i < 30:
        game_state_manager.write_game_info(f'_mantella_leave_faction_{i}', '')
        i += 1
    return

def remove_from_faction(faction_name : str, game_state_manager : game_manager.GameStateManager):
    key = sanitize_faction_name(faction_name)
    if key not in factions.keys():
        logging.info(f'The NPC tried to join the faction "{key}", but the faction isn\'t found.')
        return
    faction = factions[key]
    logging.info(f"The NPC is leaving the {faction.name}.")
    game_state_manager.write_game_info(f'_mantella_leave_faction', faction.name)
    i = 1
    for faction_formid in faction.factions:
        if len(faction_formid) > 0:
            game_state_manager.write_game_info(f'_mantella_leave_faction_{i}', faction_formid)
            i += 1
    while i < 30:
        game_state_manager.write_game_info(f'_mantella_leave_faction_{i}', '')
        i += 1
    return
