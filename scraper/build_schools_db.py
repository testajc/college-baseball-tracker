#!/usr/bin/env python3
"""
build_schools_db.py

Builds the schools_database.csv that the scraper uses.
Sources:
  1. Hardcoded known schools with verified athletics URLs
  2. Web scraping from NCAA member directories (future)

Usage:
    python build_schools_db.py             # Build from known list
    python build_schools_db.py --verify    # Verify all URLs are reachable
    python build_schools_db.py --stats     # Show stats about the database
"""

import argparse
import csv
import logging
import time
import random
from pathlib import Path
from typing import List, Dict
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent / 'schools_database.csv'

CSV_FIELDS = [
    'school_name', 'division', 'conference', 'athletics_base_url',
    'roster_url', 'stats_url', 'last_scraped', 'scrape_priority'
]

# ── Known Schools Database ──────────────────────────────────────────────
# This is a curated list of schools with verified SIDEARM athletics URLs.
# Schools are grouped by division.
# roster_url and stats_url are relative paths from athletics_base_url.

KNOWN_SCHOOLS: List[Dict] = [
    # ═══════════════════════════════════════════════════════════════
    # D1 Schools
    # ═══════════════════════════════════════════════════════════════

    # ACC
    {"school_name": "Boston College", "division": "D1", "conference": "ACC", "athletics_base_url": "https://bceagles.com"},
    {"school_name": "Clemson", "division": "D1", "conference": "ACC", "athletics_base_url": "https://clemsontigers.com", "stats_url": "https://data.clemsontigers.com/Stats/Baseball/2026/teamcume.htm"},
    {"school_name": "Duke", "division": "D1", "conference": "ACC", "athletics_base_url": "https://goduke.com"},
    {"school_name": "Florida St.", "division": "D1", "conference": "ACC", "athletics_base_url": "https://seminoles.com"},
    {"school_name": "Georgia Tech", "division": "D1", "conference": "ACC", "athletics_base_url": "https://ramblinwreck.com", "roster_url": "/sports/m-basebl/roster/"},
    {"school_name": "Louisville", "division": "D1", "conference": "ACC", "athletics_base_url": "https://gocards.com"},
    {"school_name": "Miami (FL)", "division": "D1", "conference": "ACC", "athletics_base_url": "https://miamihurricanes.com"},
    {"school_name": "North Carolina", "division": "D1", "conference": "ACC", "athletics_base_url": "https://goheels.com"},
    {"school_name": "NC State", "division": "D1", "conference": "ACC", "athletics_base_url": "https://gopack.com"},
    {"school_name": "Notre Dame", "division": "D1", "conference": "ACC", "athletics_base_url": "https://und.com"},
    {"school_name": "Pittsburgh", "division": "D1", "conference": "ACC", "athletics_base_url": "https://pittsburghpanthers.com"},
    {"school_name": "Virginia", "division": "D1", "conference": "ACC", "athletics_base_url": "https://virginiasports.com"},
    {"school_name": "Virginia Tech", "division": "D1", "conference": "ACC", "athletics_base_url": "https://hokiesports.com"},
    {"school_name": "Wake Forest", "division": "D1", "conference": "ACC", "athletics_base_url": "https://godeacs.com"},
    {"school_name": "Cal", "division": "D1", "conference": "ACC", "athletics_base_url": "https://calbears.com"},
    {"school_name": "SMU", "division": "D1", "conference": "ACC", "athletics_base_url": "https://smumustangs.com"},
    {"school_name": "Stanford", "division": "D1", "conference": "ACC", "athletics_base_url": "https://gostanford.com"},

    # SEC
    {"school_name": "Alabama", "division": "D1", "conference": "SEC", "athletics_base_url": "https://rolltide.com"},
    {"school_name": "Arkansas", "division": "D1", "conference": "SEC", "athletics_base_url": "https://arkansasrazorbacks.com", "roster_url": "/sport/m-basebl/roster/", "stats_url": "https://arkansasrazorbacks.com/stats/baseball/2026/teamcume.htm"},
    {"school_name": "Auburn", "division": "D1", "conference": "SEC", "athletics_base_url": "https://auburntigers.com"},
    {"school_name": "Florida", "division": "D1", "conference": "SEC", "athletics_base_url": "https://floridagators.com"},
    {"school_name": "Georgia", "division": "D1", "conference": "SEC", "athletics_base_url": "https://georgiadogs.com"},
    {"school_name": "Kentucky", "division": "D1", "conference": "SEC", "athletics_base_url": "https://ukathletics.com"},
    {"school_name": "LSU", "division": "D1", "conference": "SEC", "athletics_base_url": "https://lsusports.net"},
    {"school_name": "Mississippi St.", "division": "D1", "conference": "SEC", "athletics_base_url": "https://hailstate.com"},
    {"school_name": "Missouri", "division": "D1", "conference": "SEC", "athletics_base_url": "https://mutigers.com"},
    {"school_name": "Oklahoma", "division": "D1", "conference": "SEC", "athletics_base_url": "https://soonersports.com"},
    {"school_name": "Ole Miss", "division": "D1", "conference": "SEC", "athletics_base_url": "https://olemisssports.com"},
    {"school_name": "South Carolina", "division": "D1", "conference": "SEC", "athletics_base_url": "https://gamecocksonline.com"},
    {"school_name": "Tennessee", "division": "D1", "conference": "SEC", "athletics_base_url": "https://utsports.com"},
    {"school_name": "Texas", "division": "D1", "conference": "SEC", "athletics_base_url": "https://texassports.com"},
    {"school_name": "Texas A&M", "division": "D1", "conference": "SEC", "athletics_base_url": "https://12thman.com"},
    {"school_name": "Vanderbilt", "division": "D1", "conference": "SEC", "athletics_base_url": "https://vucommodores.com"},

    # Big 12
    {"school_name": "Arizona", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://arizonawildcats.com"},
    {"school_name": "Arizona St.", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://thesundevils.com"},
    {"school_name": "Baylor", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://baylorbears.com"},
    {"school_name": "BYU", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://byucougars.com"},
    {"school_name": "Cincinnati", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://gobearcats.com"},
    {"school_name": "Colorado", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://cubuffs.com"},
    {"school_name": "Houston", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://uhcougars.com"},
    {"school_name": "Iowa St.", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://cyclones.com"},
    {"school_name": "Kansas", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://kuathletics.com"},
    {"school_name": "Kansas St.", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://kstatesports.com"},
    {"school_name": "Oklahoma St.", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://okstate.com"},
    {"school_name": "TCU", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://gofrogs.com"},
    {"school_name": "Texas Tech", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://texastech.com"},
    {"school_name": "UCF", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://ucfknights.com"},
    {"school_name": "Utah", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://utahutes.com"},
    {"school_name": "West Virginia", "division": "D1", "conference": "Big 12", "athletics_base_url": "https://wvusports.com"},

    # Big Ten
    {"school_name": "Illinois", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://fightingillini.com"},
    {"school_name": "Indiana", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://iuhoosiers.com"},
    {"school_name": "Iowa", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://hawkeyesports.com"},
    {"school_name": "Maryland", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://umterps.com"},
    {"school_name": "Michigan", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://mgoblue.com"},
    {"school_name": "Michigan St.", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://msuspartans.com"},
    {"school_name": "Minnesota", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://gophersports.com"},
    {"school_name": "Nebraska", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://huskers.com"},
    {"school_name": "Northwestern", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://nusports.com"},
    {"school_name": "Ohio St.", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://ohiostatebuckeyes.com"},
    {"school_name": "Penn St.", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://gopsusports.com"},
    {"school_name": "Purdue", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://purduesports.com"},
    {"school_name": "Rutgers", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://scarletknights.com"},
    {"school_name": "UCLA", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://uclabruins.com"},
    {"school_name": "USC", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://usctrojans.com"},
    {"school_name": "Oregon", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://goducks.com"},
    {"school_name": "Oregon St.", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://osubeavers.com"},
    {"school_name": "Washington", "division": "D1", "conference": "Big Ten", "athletics_base_url": "https://gohuskies.com"},

    # Pac-12 (remaining)
    {"school_name": "Washington St.", "division": "D1", "conference": "Pac-12", "athletics_base_url": "https://wsucougars.com"},

    # AAC
    {"school_name": "Charlotte", "division": "D1", "conference": "AAC", "athletics_base_url": "https://charlotte49ers.com"},
    {"school_name": "East Carolina", "division": "D1", "conference": "AAC", "athletics_base_url": "https://ecupirates.com"},
    {"school_name": "Memphis", "division": "D1", "conference": "AAC", "athletics_base_url": "https://gotigersgo.com"},
    {"school_name": "Navy", "division": "D1", "conference": "AAC", "athletics_base_url": "https://navysports.com"},
    {"school_name": "Rice", "division": "D1", "conference": "AAC", "athletics_base_url": "https://riceowls.com"},
    {"school_name": "South Florida", "division": "D1", "conference": "AAC", "athletics_base_url": "https://gousfbulls.com"},
    {"school_name": "Tulane", "division": "D1", "conference": "AAC", "athletics_base_url": "https://tulanegreenwave.com"},
    {"school_name": "Wichita St.", "division": "D1", "conference": "AAC", "athletics_base_url": "https://goshockers.com"},

    # Sun Belt
    {"school_name": "App State", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://appstatesports.com"},
    {"school_name": "Coastal Carolina", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://goccusports.com"},
    {"school_name": "Georgia Southern", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://gseagles.com"},
    {"school_name": "Georgia St.", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://georgiastatesports.com"},
    {"school_name": "Louisiana", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://ragincajuns.com"},
    {"school_name": "Marshall", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://herdzone.com"},
    {"school_name": "Old Dominion", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://odusports.com"},
    {"school_name": "South Alabama", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://usajaguars.com"},
    {"school_name": "Southern Miss", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://southernmiss.com"},
    {"school_name": "Texas St.", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://txstatebobcats.com"},
    {"school_name": "Troy", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://troytrojans.com"},
    {"school_name": "UL Monroe", "division": "D1", "conference": "Sun Belt", "athletics_base_url": "https://ulmwarhawks.com"},

    # Conference USA
    {"school_name": "FIU", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://fiusports.com"},
    {"school_name": "Jacksonville St.", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://jsugamecocksports.com"},
    {"school_name": "Liberty", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://libertyflames.com"},
    {"school_name": "Louisiana Tech", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://latechsports.com"},
    {"school_name": "Middle Tennessee", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://goblueraiders.com"},
    {"school_name": "New Mexico St.", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://nmstatesports.com"},
    {"school_name": "Sam Houston", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://gobearkats.com"},
    {"school_name": "UTEP", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://utepminers.com"},
    {"school_name": "Western Kentucky", "division": "D1", "conference": "C-USA", "athletics_base_url": "https://wkusports.com"},

    # Colonial
    {"school_name": "College of Charleston", "division": "D1", "conference": "CAA", "athletics_base_url": "https://cofcsports.com"},
    {"school_name": "Delaware", "division": "D1", "conference": "CAA", "athletics_base_url": "https://bluehens.com"},
    {"school_name": "Elon", "division": "D1", "conference": "CAA", "athletics_base_url": "https://elonphoenix.com"},
    {"school_name": "Hofstra", "division": "D1", "conference": "CAA", "athletics_base_url": "https://gohofstra.com"},
    {"school_name": "Northeastern", "division": "D1", "conference": "CAA", "athletics_base_url": "https://nuhuskies.com"},
    {"school_name": "Stony Brook", "division": "D1", "conference": "CAA", "athletics_base_url": "https://stonybrookathletics.com"},
    {"school_name": "UNC Wilmington", "division": "D1", "conference": "CAA", "athletics_base_url": "https://uncwsports.com"},
    {"school_name": "William & Mary", "division": "D1", "conference": "CAA", "athletics_base_url": "https://tribeathletics.com"},

    # Mountain West
    {"school_name": "Air Force", "division": "D1", "conference": "MWC", "athletics_base_url": "https://goairforcefalcons.com"},
    {"school_name": "Fresno St.", "division": "D1", "conference": "MWC", "athletics_base_url": "https://gobulldogs.com"},
    {"school_name": "Nevada", "division": "D1", "conference": "MWC", "athletics_base_url": "https://nevadawolfpack.com"},
    {"school_name": "New Mexico", "division": "D1", "conference": "MWC", "athletics_base_url": "https://golobos.com"},
    {"school_name": "San Diego St.", "division": "D1", "conference": "MWC", "athletics_base_url": "https://goaztecs.com"},
    {"school_name": "San Jose St.", "division": "D1", "conference": "MWC", "athletics_base_url": "https://sjsuspartans.com"},
    {"school_name": "UNLV", "division": "D1", "conference": "MWC", "athletics_base_url": "https://unlvrebels.com"},

    # Big East
    {"school_name": "Connecticut", "division": "D1", "conference": "Big East", "athletics_base_url": "https://uconnhuskies.com"},
    {"school_name": "Creighton", "division": "D1", "conference": "Big East", "athletics_base_url": "https://gocreighton.com"},
    {"school_name": "Georgetown", "division": "D1", "conference": "Big East", "athletics_base_url": "https://guhoyas.com"},
    {"school_name": "Providence", "division": "D1", "conference": "Big East", "athletics_base_url": "https://friars.com"},
    {"school_name": "Seton Hall", "division": "D1", "conference": "Big East", "athletics_base_url": "https://shupirates.com"},
    {"school_name": "St. John's", "division": "D1", "conference": "Big East", "athletics_base_url": "https://redstormsports.com"},
    {"school_name": "Villanova", "division": "D1", "conference": "Big East", "athletics_base_url": "https://villanova.com"},
    {"school_name": "Xavier", "division": "D1", "conference": "Big East", "athletics_base_url": "https://goxavier.com"},
    {"school_name": "Butler", "division": "D1", "conference": "Big East", "athletics_base_url": "https://butlersports.com"},

    # A-10
    {"school_name": "Dayton", "division": "D1", "conference": "A-10", "athletics_base_url": "https://daytonflyers.com"},
    {"school_name": "George Mason", "division": "D1", "conference": "A-10", "athletics_base_url": "https://gomason.com"},
    {"school_name": "George Washington", "division": "D1", "conference": "A-10", "athletics_base_url": "https://gwsports.com"},
    {"school_name": "La Salle", "division": "D1", "conference": "A-10", "athletics_base_url": "https://goexplorers.com"},
    {"school_name": "Rhode Island", "division": "D1", "conference": "A-10", "athletics_base_url": "https://gorhody.com"},
    {"school_name": "Richmond", "division": "D1", "conference": "A-10", "athletics_base_url": "https://richmondspiders.com"},
    {"school_name": "Saint Louis", "division": "D1", "conference": "A-10", "athletics_base_url": "https://slubillikens.com"},
    {"school_name": "VCU", "division": "D1", "conference": "A-10", "athletics_base_url": "https://vcuathletics.com"},

    # WCC
    {"school_name": "Gonzaga", "division": "D1", "conference": "WCC", "athletics_base_url": "https://gozags.com"},
    {"school_name": "LMU", "division": "D1", "conference": "WCC", "athletics_base_url": "https://lmulions.com"},
    {"school_name": "Pepperdine", "division": "D1", "conference": "WCC", "athletics_base_url": "https://pepperdinewaves.com"},
    {"school_name": "San Diego", "division": "D1", "conference": "WCC", "athletics_base_url": "https://usdtoreros.com"},
    {"school_name": "San Francisco", "division": "D1", "conference": "WCC", "athletics_base_url": "https://usfdons.com"},
    {"school_name": "Santa Clara", "division": "D1", "conference": "WCC", "athletics_base_url": "https://santaclarabroncos.com"},
    {"school_name": "Pacific", "division": "D1", "conference": "WCC", "athletics_base_url": "https://pacifictigers.com"},
    {"school_name": "Portland", "division": "D1", "conference": "WCC", "athletics_base_url": "https://portlandpilots.com"},

    # Ivy League
    {"school_name": "Columbia", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://gocolumbialions.com"},
    {"school_name": "Cornell", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://cornellbigred.com"},
    {"school_name": "Dartmouth", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://dartmouthsports.com"},
    {"school_name": "Harvard", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://gocrimson.com"},
    {"school_name": "Penn", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://pennathletics.com"},
    {"school_name": "Princeton", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://goprincetontigers.com"},
    {"school_name": "Yale", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://yalebulldogs.com"},
    {"school_name": "Brown", "division": "D1", "conference": "Ivy", "athletics_base_url": "https://brownbears.com"},

    # Patriot League
    {"school_name": "Army", "division": "D1", "conference": "Patriot", "athletics_base_url": "https://goarmywestpoint.com"},
    {"school_name": "Bucknell", "division": "D1", "conference": "Patriot", "athletics_base_url": "https://bucknellbison.com"},
    {"school_name": "Holy Cross", "division": "D1", "conference": "Patriot", "athletics_base_url": "https://goholycross.com"},
    {"school_name": "Lafayette", "division": "D1", "conference": "Patriot", "athletics_base_url": "https://goleopards.com"},
    {"school_name": "Lehigh", "division": "D1", "conference": "Patriot", "athletics_base_url": "https://lehighsports.com"},

    # MEAC
    {"school_name": "Coppin St.", "division": "D1", "conference": "MEAC", "athletics_base_url": "https://coppinstatesports.com"},
    {"school_name": "Delaware St.", "division": "D1", "conference": "MEAC", "athletics_base_url": "https://dsuhornets.com"},
    {"school_name": "Norfolk St.", "division": "D1", "conference": "MEAC", "athletics_base_url": "https://nsuspartans.com"},

    # SWAC
    {"school_name": "Alabama St.", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://bamastatesports.com"},
    {"school_name": "Alcorn", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://alcornsports.com"},
    {"school_name": "Grambling", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://gsutigers.com"},
    {"school_name": "Jackson St.", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://gojsutigers.com"},
    {"school_name": "Prairie View A&M", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://pvpanthers.com"},
    {"school_name": "Southern", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://gojagsports.com"},
    {"school_name": "Texas Southern", "division": "D1", "conference": "SWAC", "athletics_base_url": "https://tsusports.com"},

    # America East
    {"school_name": "Binghamton", "division": "D1", "conference": "America East", "athletics_base_url": "https://bubearcats.com"},
    {"school_name": "Hartford", "division": "D1", "conference": "America East", "athletics_base_url": "https://hartfordhawks.com"},
    {"school_name": "Maine", "division": "D1", "conference": "America East", "athletics_base_url": "https://goblackbears.com"},
    {"school_name": "UMBC", "division": "D1", "conference": "America East", "athletics_base_url": "https://umbcretrievers.com"},
    {"school_name": "UMass Lowell", "division": "D1", "conference": "America East", "athletics_base_url": "https://goriverhawks.com"},

    # Big South
    {"school_name": "Campbell", "division": "D1", "conference": "Big South", "athletics_base_url": "https://gocamels.com"},
    {"school_name": "Charleston Southern", "division": "D1", "conference": "Big South", "athletics_base_url": "https://csusports.com"},
    {"school_name": "Gardner-Webb", "division": "D1", "conference": "Big South", "athletics_base_url": "https://gwusports.com"},
    {"school_name": "High Point", "division": "D1", "conference": "Big South", "athletics_base_url": "https://highpointpanthers.com"},
    {"school_name": "Longwood", "division": "D1", "conference": "Big South", "athletics_base_url": "https://longwoodlancers.com"},
    {"school_name": "Presbyterian", "division": "D1", "conference": "Big South", "athletics_base_url": "https://gobluehose.com"},
    {"school_name": "Radford", "division": "D1", "conference": "Big South", "athletics_base_url": "https://radfordathletics.com"},
    {"school_name": "UNC Asheville", "division": "D1", "conference": "Big South", "athletics_base_url": "https://uncabulldogs.com"},
    {"school_name": "Winthrop", "division": "D1", "conference": "Big South", "athletics_base_url": "https://winthropeagles.com"},

    # Horizon League
    {"school_name": "Milwaukee", "division": "D1", "conference": "Horizon", "athletics_base_url": "https://mkepanthers.com"},
    {"school_name": "Northern Kentucky", "division": "D1", "conference": "Horizon", "athletics_base_url": "https://nkunorse.com"},
    {"school_name": "Oakland", "division": "D1", "conference": "Horizon", "athletics_base_url": "https://goldengrizzlies.com"},
    {"school_name": "Wright St.", "division": "D1", "conference": "Horizon", "athletics_base_url": "https://wsuraiders.com"},
    {"school_name": "Youngstown St.", "division": "D1", "conference": "Horizon", "athletics_base_url": "https://ysusports.com"},

    # MAAC
    {"school_name": "Canisius", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://gogriffs.com"},
    {"school_name": "Fairfield", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://fairfieldstags.com"},
    {"school_name": "Iona", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://icgaels.com"},
    {"school_name": "Manhattan", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://gojaspers.com"},
    {"school_name": "Marist", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://goredfoxes.com"},
    {"school_name": "Niagara", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://purpleeagles.com"},
    {"school_name": "Quinnipiac", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://quinnipiacbobcats.com"},
    {"school_name": "Rider", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://gobroncs.com"},
    {"school_name": "St. Peter's", "division": "D1", "conference": "MAAC", "athletics_base_url": "https://saintpeterspeacocks.com"},

    # MAC
    {"school_name": "Ball St.", "division": "D1", "conference": "MAC", "athletics_base_url": "https://ballstatesports.com"},
    {"school_name": "Bowling Green", "division": "D1", "conference": "MAC", "athletics_base_url": "https://bgsufalcons.com"},
    {"school_name": "Central Michigan", "division": "D1", "conference": "MAC", "athletics_base_url": "https://cmuchippewas.com"},
    {"school_name": "Eastern Michigan", "division": "D1", "conference": "MAC", "athletics_base_url": "https://emueagles.com"},
    {"school_name": "Kent St.", "division": "D1", "conference": "MAC", "athletics_base_url": "https://kentstatesports.com"},
    {"school_name": "Miami (OH)", "division": "D1", "conference": "MAC", "athletics_base_url": "https://miamiredhawks.com"},
    {"school_name": "Northern Illinois", "division": "D1", "conference": "MAC", "athletics_base_url": "https://niuhuskies.com"},
    {"school_name": "Ohio", "division": "D1", "conference": "MAC", "athletics_base_url": "https://ohiobobcats.com"},
    {"school_name": "Toledo", "division": "D1", "conference": "MAC", "athletics_base_url": "https://utrockets.com"},
    {"school_name": "Western Michigan", "division": "D1", "conference": "MAC", "athletics_base_url": "https://wmubroncos.com"},

    # Missouri Valley
    {"school_name": "Bradley", "division": "D1", "conference": "MVC", "athletics_base_url": "https://bradleybraves.com"},
    {"school_name": "Dallas Baptist", "division": "D1", "conference": "MVC", "athletics_base_url": "https://dbupatriots.com"},
    {"school_name": "Evansville", "division": "D1", "conference": "MVC", "athletics_base_url": "https://gopurpleaces.com"},
    {"school_name": "Illinois St.", "division": "D1", "conference": "MVC", "athletics_base_url": "https://goredbirds.com"},
    {"school_name": "Indiana St.", "division": "D1", "conference": "MVC", "athletics_base_url": "https://gosycamores.com"},
    {"school_name": "Missouri St.", "division": "D1", "conference": "MVC", "athletics_base_url": "https://missouristatebears.com"},
    {"school_name": "Southern Illinois", "division": "D1", "conference": "MVC", "athletics_base_url": "https://siusalukis.com"},
    {"school_name": "Valparaiso", "division": "D1", "conference": "MVC", "athletics_base_url": "https://valpoathletics.com"},

    # OVC
    {"school_name": "Belmont", "division": "D1", "conference": "OVC", "athletics_base_url": "https://belmontbruins.com"},
    {"school_name": "Eastern Illinois", "division": "D1", "conference": "OVC", "athletics_base_url": "https://eiupanthers.com"},
    {"school_name": "Morehead St.", "division": "D1", "conference": "OVC", "athletics_base_url": "https://msueagles.com"},
    {"school_name": "Murray St.", "division": "D1", "conference": "OVC", "athletics_base_url": "https://goracers.com"},
    {"school_name": "SE Missouri", "division": "D1", "conference": "OVC", "athletics_base_url": "https://gosoutheast.com"},
    {"school_name": "SIU Edwardsville", "division": "D1", "conference": "OVC", "athletics_base_url": "https://siuecougars.com"},
    {"school_name": "UT Martin", "division": "D1", "conference": "OVC", "athletics_base_url": "https://utmsports.com"},

    # Southern
    {"school_name": "The Citadel", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://citadelsports.com"},
    {"school_name": "ETSU", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://etsubucs.com"},
    {"school_name": "Furman", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://furmanpaladins.com"},
    {"school_name": "Mercer", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://mercerbears.com"},
    {"school_name": "Samford", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://samfordsports.com"},
    {"school_name": "UNC Greensboro", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://uncgspartans.com"},
    {"school_name": "VMI", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://vmikeydets.com"},
    {"school_name": "Western Carolina", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://catamountsports.com"},
    {"school_name": "Wofford", "division": "D1", "conference": "SoCon", "athletics_base_url": "https://woffordterriers.com"},

    # Southland
    {"school_name": "Houston Christian", "division": "D1", "conference": "Southland", "athletics_base_url": "https://hcuhuskies.com"},
    {"school_name": "Incarnate Word", "division": "D1", "conference": "Southland", "athletics_base_url": "https://uiwcardinals.com"},
    {"school_name": "Lamar", "division": "D1", "conference": "Southland", "athletics_base_url": "https://lamarcardinals.com"},
    {"school_name": "McNeese", "division": "D1", "conference": "Southland", "athletics_base_url": "https://mcneesesports.com"},
    {"school_name": "New Orleans", "division": "D1", "conference": "Southland", "athletics_base_url": "https://unoprivateers.com"},
    {"school_name": "Nicholls", "division": "D1", "conference": "Southland", "athletics_base_url": "https://geauxcolonels.com"},
    {"school_name": "Northwestern St.", "division": "D1", "conference": "Southland", "athletics_base_url": "https://naborssports.com"},
    {"school_name": "Southeastern Louisiana", "division": "D1", "conference": "Southland", "athletics_base_url": "https://lionsports.net"},
    {"school_name": "Texas A&M-CC", "division": "D1", "conference": "Southland", "athletics_base_url": "https://goislanders.com"},

    # WAC
    {"school_name": "Abilene Christian", "division": "D1", "conference": "WAC", "athletics_base_url": "https://acusports.com"},
    {"school_name": "Grand Canyon", "division": "D1", "conference": "WAC", "athletics_base_url": "https://gculopes.com"},
    {"school_name": "Tarleton", "division": "D1", "conference": "WAC", "athletics_base_url": "https://tarletonsports.com"},
    {"school_name": "Utah Valley", "division": "D1", "conference": "WAC", "athletics_base_url": "https://gouvu.com"},
    {"school_name": "Seattle U", "division": "D1", "conference": "WAC", "athletics_base_url": "https://goseattleu.com"},

    # ASUN
    {"school_name": "Central Arkansas", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://ucasports.com"},
    {"school_name": "Eastern Kentucky", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://ekusports.com"},
    {"school_name": "Florida Gulf Coast", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://fgcuathletics.com"},
    {"school_name": "Jacksonville", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://judolphins.com"},
    {"school_name": "Kennesaw St.", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://ksuowls.com"},
    {"school_name": "Lipscomb", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://lipscombsports.com"},
    {"school_name": "North Alabama", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://roarlions.com"},
    {"school_name": "Queens", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://queensathletics.com"},
    {"school_name": "Stetson", "division": "D1", "conference": "ASUN", "athletics_base_url": "https://gohatters.com"},

    # NEC
    {"school_name": "Central Connecticut", "division": "D1", "conference": "NEC", "athletics_base_url": "https://ccsubluedevils.com"},
    {"school_name": "Fairleigh Dickinson", "division": "D1", "conference": "NEC", "athletics_base_url": "https://fduknights.com"},
    {"school_name": "Le Moyne", "division": "D1", "conference": "NEC", "athletics_base_url": "https://lemoynedolphins.com"},
    {"school_name": "LIU", "division": "D1", "conference": "NEC", "athletics_base_url": "https://liuathletics.com"},
    {"school_name": "Merrimack", "division": "D1", "conference": "NEC", "athletics_base_url": "https://merrimackathletics.com"},
    {"school_name": "Sacred Heart", "division": "D1", "conference": "NEC", "athletics_base_url": "https://sacredheartpioneers.com"},
    {"school_name": "St. Francis (PA)", "division": "D1", "conference": "NEC", "athletics_base_url": "https://sfuathletics.com"},
    {"school_name": "Wagner", "division": "D1", "conference": "NEC", "athletics_base_url": "https://wagnerathletics.com"},

    # Summit League
    {"school_name": "Oral Roberts", "division": "D1", "conference": "Summit", "athletics_base_url": "https://oruathletics.com"},
    {"school_name": "South Dakota St.", "division": "D1", "conference": "Summit", "athletics_base_url": "https://gojacks.com"},
    {"school_name": "North Dakota St.", "division": "D1", "conference": "Summit", "athletics_base_url": "https://gobison.com"},
    {"school_name": "Omaha", "division": "D1", "conference": "Summit", "athletics_base_url": "https://omavs.com"},
    {"school_name": "Western Illinois", "division": "D1", "conference": "Summit", "athletics_base_url": "https://goleathernecks.com"},

    # Big West
    {"school_name": "Cal Poly", "division": "D1", "conference": "Big West", "athletics_base_url": "https://gopoly.com"},
    {"school_name": "Cal St. Fullerton", "division": "D1", "conference": "Big West", "athletics_base_url": "https://fullertontitans.com"},
    {"school_name": "Cal St. Northridge", "division": "D1", "conference": "Big West", "athletics_base_url": "https://gomatadors.com"},
    {"school_name": "Hawaii", "division": "D1", "conference": "Big West", "athletics_base_url": "https://hawaiiathletics.com"},
    {"school_name": "Long Beach St.", "division": "D1", "conference": "Big West", "athletics_base_url": "https://longbeachstate.com"},
    {"school_name": "UC Davis", "division": "D1", "conference": "Big West", "athletics_base_url": "https://ucdavisaggies.com"},
    {"school_name": "UC Irvine", "division": "D1", "conference": "Big West", "athletics_base_url": "https://ucirvinesports.com"},
    {"school_name": "UC Riverside", "division": "D1", "conference": "Big West", "athletics_base_url": "https://gohighlanders.com"},
    {"school_name": "UC San Diego", "division": "D1", "conference": "Big West", "athletics_base_url": "https://ucsdtritons.com"},
    {"school_name": "UC Santa Barbara", "division": "D1", "conference": "Big West", "athletics_base_url": "https://ucsbgauchos.com"},

    # ═══════════════════════════════════════════════════════════════
    # D2 Schools - Comprehensive List
    # ═══════════════════════════════════════════════════════════════

    # ── SSC (Sunshine State Conference) ───────────────────────────
    {"school_name": "Tampa", "division": "D2", "conference": "SSC", "athletics_base_url": "https://tampaspartans.com"},
    {"school_name": "Rollins", "division": "D2", "conference": "SSC", "athletics_base_url": "https://rollinssports.com"},
    {"school_name": "Nova Southeastern", "division": "D2", "conference": "SSC", "athletics_base_url": "https://nsusharks.com"},
    {"school_name": "Florida Southern", "division": "D2", "conference": "SSC", "athletics_base_url": "https://fscmocs.com"},
    {"school_name": "Lynn", "division": "D2", "conference": "SSC", "athletics_base_url": "https://lynnfightingknights.com"},
    {"school_name": "Barry", "division": "D2", "conference": "SSC", "athletics_base_url": "https://gobarrybucs.com"},
    {"school_name": "Embry-Riddle", "division": "D2", "conference": "SSC", "athletics_base_url": "https://erauathletics.com"},
    {"school_name": "Saint Leo", "division": "D2", "conference": "SSC", "athletics_base_url": "https://saintleolions.com"},
    {"school_name": "Palm Beach Atlantic", "division": "D2", "conference": "SSC", "athletics_base_url": "https://pbau.com"},
    {"school_name": "Eckerd", "division": "D2", "conference": "SSC", "athletics_base_url": "https://eckerdtritons.com"},
    {"school_name": "Florida Tech", "division": "D2", "conference": "SSC", "athletics_base_url": "https://floridatechsports.com"},

    # ── GSC (Gulf South Conference) ───────────────────────────────
    {"school_name": "West Florida", "division": "D2", "conference": "GSC", "athletics_base_url": "https://goargos.com"},
    {"school_name": "North Greenville", "division": "D2", "conference": "GSC", "athletics_base_url": "https://ngucrusaders.com"},
    {"school_name": "Valdosta St.", "division": "D2", "conference": "GSC", "athletics_base_url": "https://vstateblazers.com"},
    {"school_name": "Delta St.", "division": "D2", "conference": "GSC", "athletics_base_url": "https://gostatesmen.com"},
    {"school_name": "West Alabama", "division": "D2", "conference": "GSC", "athletics_base_url": "https://uwaathletics.com"},
    {"school_name": "Lee", "division": "D2", "conference": "GSC", "athletics_base_url": "https://leeflames.com"},
    {"school_name": "Shorter", "division": "D2", "conference": "GSC", "athletics_base_url": "https://shorterhawks.com"},
    {"school_name": "West Georgia", "division": "D2", "conference": "GSC", "athletics_base_url": "https://uwgathletics.com"},
    {"school_name": "Mississippi College", "division": "D2", "conference": "GSC", "athletics_base_url": "https://gochoctaws.com"},
    {"school_name": "Christian Brothers", "division": "D2", "conference": "GSC", "athletics_base_url": "https://cbubuccaneers.com"},
    {"school_name": "Auburn Montgomery", "division": "D2", "conference": "GSC", "athletics_base_url": "https://aumathletics.com"},
    {"school_name": "Alabama Huntsville", "division": "D2", "conference": "GSC", "athletics_base_url": "https://uahchargers.com"},
    {"school_name": "Union (TN)", "division": "D2", "conference": "GSC", "athletics_base_url": "https://uubulldogs.com"},

    # ── PBC (Peach Belt Conference) ───────────────────────────────
    {"school_name": "Lander", "division": "D2", "conference": "PBC", "athletics_base_url": "https://landerbearcats.com"},
    {"school_name": "USC Aiken", "division": "D2", "conference": "PBC", "athletics_base_url": "https://pacersports.com"},
    {"school_name": "Young Harris", "division": "D2", "conference": "PBC", "athletics_base_url": "https://yhcathletics.com"},
    {"school_name": "Georgia Southwestern", "division": "D2", "conference": "PBC", "athletics_base_url": "https://gswcanes.com"},
    {"school_name": "Georgia College", "division": "D2", "conference": "PBC", "athletics_base_url": "https://gcbobcats.com"},
    {"school_name": "UNC Pembroke", "division": "D2", "conference": "PBC", "athletics_base_url": "https://uncpbraves.com"},
    {"school_name": "Columbus St.", "division": "D2", "conference": "PBC", "athletics_base_url": "https://csucougars.com"},
    {"school_name": "Flagler", "division": "D2", "conference": "PBC", "athletics_base_url": "https://flaglerathletics.com"},
    {"school_name": "Francis Marion", "division": "D2", "conference": "PBC", "athletics_base_url": "https://fmupatriots.com"},
    {"school_name": "Clayton St.", "division": "D2", "conference": "PBC", "athletics_base_url": "https://claytonstatesports.com"},
    {"school_name": "Augusta", "division": "D2", "conference": "PBC", "athletics_base_url": "https://augustajags.com"},
    {"school_name": "SC Aiken", "division": "D2", "conference": "PBC", "athletics_base_url": "https://pacersports.com"},

    # ── SAC (South Atlantic Conference) ───────────────────────────
    {"school_name": "Catawba", "division": "D2", "conference": "SAC", "athletics_base_url": "https://gocatawbaindians.com"},
    {"school_name": "Wingate", "division": "D2", "conference": "SAC", "athletics_base_url": "https://wingatebulldogs.com"},
    {"school_name": "Lenoir-Rhyne", "division": "D2", "conference": "SAC", "athletics_base_url": "https://lrbears.com"},
    {"school_name": "Lincoln Memorial", "division": "D2", "conference": "SAC", "athletics_base_url": "https://lmurailsplitters.com"},
    {"school_name": "Anderson (SC)", "division": "D2", "conference": "SAC", "athletics_base_url": "https://andersontrojans.com"},
    {"school_name": "Carson-Newman", "division": "D2", "conference": "SAC", "athletics_base_url": "https://cneagles.com"},
    {"school_name": "Mars Hill", "division": "D2", "conference": "SAC", "athletics_base_url": "https://marshilllions.com"},
    {"school_name": "Tusculum", "division": "D2", "conference": "SAC", "athletics_base_url": "https://tusculumpioneers.com"},
    {"school_name": "Newberry", "division": "D2", "conference": "SAC", "athletics_base_url": "https://newberrywolves.com"},
    {"school_name": "Coker", "division": "D2", "conference": "SAC", "athletics_base_url": "https://cokercobras.com"},
    {"school_name": "Queens (NC)", "division": "D2", "conference": "SAC", "athletics_base_url": "https://queensroyals.com"},
    {"school_name": "Emory & Henry", "division": "D2", "conference": "SAC", "athletics_base_url": "https://ehcwasps.com"},

    # ── Conference Carolinas ──────────────────────────────────────
    {"school_name": "Mount Olive", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://mountolivetrojans.com"},
    {"school_name": "Barton", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://bartonbulldogs.com"},
    {"school_name": "Belmont Abbey", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://abbeyathletics.com"},
    {"school_name": "Converse", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://goconverse.com"},
    {"school_name": "Emmanuel (GA)", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://ecgalions.com"},
    {"school_name": "Erskine", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://erskinesports.com"},
    {"school_name": "King (TN)", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://gotornado.com"},
    {"school_name": "North Carolina-Pembroke", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://uncpbraves.com"},
    {"school_name": "Chowan", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://gochowanhawks.com"},
    {"school_name": "Southern Wesleyan", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://swuwarriors.com"},
    {"school_name": "St. Andrews", "division": "D2", "conference": "Conference Carolinas", "athletics_base_url": "https://saknights.com"},

    # ── CACC (Central Atlantic Collegiate Conference) ─────────────
    {"school_name": "Dominican (NY)", "division": "D2", "conference": "CACC", "athletics_base_url": "https://ducharmers.com"},
    {"school_name": "Felician", "division": "D2", "conference": "CACC", "athletics_base_url": "https://feliciangoldeneagles.com"},
    {"school_name": "Goldey-Beacom", "division": "D2", "conference": "CACC", "athletics_base_url": "https://gbcathletics.com"},
    {"school_name": "Holy Family", "division": "D2", "conference": "CACC", "athletics_base_url": "https://holyfamilytigers.com"},
    {"school_name": "Bloomfield", "division": "D2", "conference": "CACC", "athletics_base_url": "https://bloomfieldathletics.com"},
    {"school_name": "Caldwell", "division": "D2", "conference": "CACC", "athletics_base_url": "https://caldwellcougars.com"},
    {"school_name": "Concordia (NY)", "division": "D2", "conference": "CACC", "athletics_base_url": "https://concordia-ny.edu/athletics"},
    {"school_name": "Georgian Court", "division": "D2", "conference": "CACC", "athletics_base_url": "https://gcuathletics.com"},
    {"school_name": "Nyack", "division": "D2", "conference": "CACC", "athletics_base_url": "https://nyackwarriors.com"},
    {"school_name": "Post", "division": "D2", "conference": "CACC", "athletics_base_url": "https://posteagles.com"},
    {"school_name": "Wilmington (DE)", "division": "D2", "conference": "CACC", "athletics_base_url": "https://wilmu.edu/athletics"},
    {"school_name": "Jefferson", "division": "D2", "conference": "CACC", "athletics_base_url": "https://jeffersonrams.com"},

    # ── NE10 (Northeast-10 Conference) ────────────────────────────
    {"school_name": "Southern New Hampshire", "division": "D2", "conference": "NE10", "athletics_base_url": "https://snhupenmen.com"},
    {"school_name": "Franklin Pierce", "division": "D2", "conference": "NE10", "athletics_base_url": "https://fpuravens.com"},
    {"school_name": "Adelphi", "division": "D2", "conference": "NE10", "athletics_base_url": "https://aupanthers.com"},
    {"school_name": "Assumption", "division": "D2", "conference": "NE10", "athletics_base_url": "https://assumptiongreyhounds.com"},
    {"school_name": "Bentley", "division": "D2", "conference": "NE10", "athletics_base_url": "https://bentleyfalcons.com"},
    {"school_name": "Le Moyne", "division": "D2", "conference": "NE10", "athletics_base_url": "https://lemoynedolphins.com"},
    {"school_name": "Merrimack", "division": "D2", "conference": "NE10", "athletics_base_url": "https://merrimackathletics.com"},
    {"school_name": "New Haven", "division": "D2", "conference": "NE10", "athletics_base_url": "https://newhavenchargers.com"},
    {"school_name": "Pace", "division": "D2", "conference": "NE10", "athletics_base_url": "https://pacesetters.com"},
    {"school_name": "Saint Anselm", "division": "D2", "conference": "NE10", "athletics_base_url": "https://saintanselmhawks.com"},
    {"school_name": "Saint Michael's", "division": "D2", "conference": "NE10", "athletics_base_url": "https://smcpurpleknights.com"},
    {"school_name": "Saint Rose", "division": "D2", "conference": "NE10", "athletics_base_url": "https://stroseathletics.com"},
    {"school_name": "Stonehill", "division": "D2", "conference": "NE10", "athletics_base_url": "https://stonehillskyhawks.com"},

    # ── ECC (East Coast Conference) ───────────────────────────────
    {"school_name": "Molloy", "division": "D2", "conference": "ECC", "athletics_base_url": "https://molloylions.com"},
    {"school_name": "Roberts Wesleyan", "division": "D2", "conference": "ECC", "athletics_base_url": "https://rwcredhawks.com"},
    {"school_name": "Daemen", "division": "D2", "conference": "ECC", "athletics_base_url": "https://daemenwildcats.com"},
    {"school_name": "New York Tech", "division": "D2", "conference": "ECC", "athletics_base_url": "https://nyaborathletics.com"},
    {"school_name": "Queens (NY)", "division": "D2", "conference": "ECC", "athletics_base_url": "https://qcknights.com"},
    {"school_name": "St. Thomas Aquinas", "division": "D2", "conference": "ECC", "athletics_base_url": "https://stacathletics.com"},
    {"school_name": "D'Youville", "division": "D2", "conference": "ECC", "athletics_base_url": "https://dyouvillesaints.com"},
    {"school_name": "LIU Post", "division": "D2", "conference": "ECC", "athletics_base_url": "https://liupostpioneers.com"},

    # ── PSAC (Pennsylvania State Athletic Conference) ─────────────
    {"school_name": "Millersville", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://millersvilleathletics.com"},
    {"school_name": "West Chester", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://wcupathletics.com"},
    {"school_name": "Shippensburg", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://shipraiders.com"},
    {"school_name": "Seton Hill", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://setonhillgriffinssports.com"},
    {"school_name": "Mercyhurst", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://hurstathletics.com"},
    {"school_name": "Slippery Rock", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://sruathletics.com"},
    {"school_name": "Kutztown", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://kutztownbears.com"},
    {"school_name": "Lock Haven", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://lockhavenathletics.com"},
    {"school_name": "East Stroudsburg", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://esuwarriors.com"},
    {"school_name": "Mansfield", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://gomounties.com"},
    {"school_name": "California (PA)", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://calvulcans.com"},
    {"school_name": "Indiana (PA)", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://iuphawks.com"},
    {"school_name": "Bloomsburg", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://buhuskies.com"},
    {"school_name": "Gannon", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://gannonathletics.com"},
    {"school_name": "Clarion", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://clariongoldeneagles.com"},
    {"school_name": "Edinboro", "division": "D2", "conference": "PSAC", "athletics_base_url": "https://edinborosports.com"},

    # ── CIAA (Central Intercollegiate Athletic Association) ────────
    {"school_name": "Fayetteville St.", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://fsubroncos.com"},
    {"school_name": "Shaw", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://shawbears.com"},
    {"school_name": "Winston-Salem St.", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://wssrams.com"},
    {"school_name": "Virginia St.", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://vsutrojans.com"},
    {"school_name": "Virginia Union", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://vuupanthers.com"},
    {"school_name": "Elizabeth City St.", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://ecsuvikings.com"},
    {"school_name": "Livingstone", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://livingstoneathletics.com"},
    {"school_name": "St. Augustine's", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://saufalcons.com"},
    {"school_name": "Johnson C. Smith", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://jcsugoldenbulls.com"},
    {"school_name": "Claflin", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://claflinathletics.com"},
    {"school_name": "Bowie St.", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://bsubulldogs.com"},
    {"school_name": "Lincoln (PA)", "division": "D2", "conference": "CIAA", "athletics_base_url": "https://lincolnlions.com"},

    # ── SIAC (Southern Intercollegiate Athletic Conference) ────────
    {"school_name": "Albany St. (GA)", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://asurams.com"},
    {"school_name": "Benedict", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://benedicttigers.com"},
    {"school_name": "Clark Atlanta", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://caupanthers.com"},
    {"school_name": "Fort Valley St.", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://fvsuwildcats.com"},
    {"school_name": "Kentucky St.", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://kysuathletics.com"},
    {"school_name": "Lane", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://lanedragons.com"},
    {"school_name": "LeMoyne-Owen", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://locmagicians.com"},
    {"school_name": "Miles", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://milesgoldenbears.com"},
    {"school_name": "Morehouse", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://morehouseathletics.com"},
    {"school_name": "Paine", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://painelions.com"},
    {"school_name": "Savannah St.", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://ssuathletics.com"},
    {"school_name": "Spring Hill", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://shcbadgers.com"},
    {"school_name": "Stillman", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://stillmanathletics.com"},
    {"school_name": "Tuskegee", "division": "D2", "conference": "SIAC", "athletics_base_url": "https://tuskegeegoldentigers.com"},

    # ── GLVC (Great Lakes Valley Conference) ──────────────────────
    {"school_name": "Indianapolis", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://uindyathletics.com"},
    {"school_name": "Southern Indiana", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://gouscreamingeagles.com"},
    {"school_name": "Drury", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://drurypanthers.com"},
    {"school_name": "Quincy", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://quincyhawks.com"},
    {"school_name": "Lewis", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://lewisflyers.com"},
    {"school_name": "McKendree", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://mckbearcats.com"},
    {"school_name": "Maryville (MO)", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://maryvillesaints.com"},
    {"school_name": "Missouri S&T", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://minerathletics.com"},
    {"school_name": "Rockhurst", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://rockhursthawks.com"},
    {"school_name": "Truman St.", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://trumanbulldogs.com"},
    {"school_name": "William Jewell", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://jewellcardinals.com"},
    {"school_name": "Southwest Baptist", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://sbubearcat.com"},
    {"school_name": "Illinois Springfield", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://uisprairiestars.com"},
    {"school_name": "Cedarville", "division": "D2", "conference": "GLVC", "athletics_base_url": "https://cedarvilleyellowjackets.com"},

    # ── G-MAC (Great Midwest Athletic Conference) ─────────────────
    {"school_name": "Tiffin", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://gotiffindragons.com"},
    {"school_name": "Findlay", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://findlayoilers.com"},
    {"school_name": "Ohio Dominican", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://ohiodominicanpanthers.com"},
    {"school_name": "Walsh", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://walshcavaliers.com"},
    {"school_name": "Malone", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://maborathletics.com"},
    {"school_name": "Hillsdale", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://hillsdalechargers.com"},
    {"school_name": "Alderson Broaddus", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://abbattlers.com"},
    {"school_name": "Davis & Elkins", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://desenatorsathletics.com"},
    {"school_name": "Kentucky Wesleyan", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://kwcpanthers.com"},
    {"school_name": "Lake Erie", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://lakeeriestorm.com"},
    {"school_name": "Ursuline", "division": "D2", "conference": "G-MAC", "athletics_base_url": "https://ursulinearrows.com"},

    # ── GLIAC (Great Lakes Intercollegiate Athletic Conference) ────
    {"school_name": "Ashland", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://goashlandeagles.com"},
    {"school_name": "Wayne St. (MI)", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://wsuwarriors.com"},
    {"school_name": "Grand Valley St.", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://gvsulakers.com"},
    {"school_name": "Saginaw Valley St.", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://svsuathletics.com"},
    {"school_name": "Northwood", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://northwoodtimberwolves.com"},
    {"school_name": "Davenport", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://davenportpanthers.com"},
    {"school_name": "Ferris St.", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://ferrissportsupdate.com"},
    {"school_name": "Lake Superior St.", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://lssulakers.com"},
    {"school_name": "Michigan Tech", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://mtuhuskies.com"},
    {"school_name": "Wisconsin-Parkside", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://parksiderangers.com"},
    {"school_name": "Purdue Northwest", "division": "D2", "conference": "GLIAC", "athletics_base_url": "https://pnwathletics.com"},

    # ── NSIC (Northern Sun Intercollegiate Conference) ────────────
    {"school_name": "Augustana (SD)", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://goaugie.com"},
    {"school_name": "Minnesota St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://maverickssports.com"},
    {"school_name": "St. Cloud St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://scsuhuskies.com"},
    {"school_name": "Wayne St. (NE)", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://wscwildcats.com"},
    {"school_name": "Winona St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://winonastatewarriors.com"},
    {"school_name": "Minnesota Duluth", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://umdbulldogs.com"},
    {"school_name": "Concordia-St. Paul", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://caborathletics.com"},
    {"school_name": "Upper Iowa", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://uiupeacocks.com"},
    {"school_name": "Minnesota Crookston", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://goldeneaglesports.com"},
    {"school_name": "Sioux Falls", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://usfcougars.com"},
    {"school_name": "Southwest Minnesota St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://smsumustangs.com"},
    {"school_name": "Bemidji St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://bsubeavers.com"},
    {"school_name": "Northern St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://nsuwolves.com"},
    {"school_name": "University of Mary", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://goumary.com"},
    {"school_name": "Minot St.", "division": "D2", "conference": "NSIC", "athletics_base_url": "https://maborathletics.com"},

    # ── MIAA (Mid-America Intercollegiate Athletics Association) ──
    {"school_name": "Central Missouri", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://ucmathletics.com"},
    {"school_name": "Pittsburg St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://pittstgorillas.com"},
    {"school_name": "Emporia St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://gohornetsonline.com"},
    {"school_name": "Northwest Missouri St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://bearcat-athletics.com"},
    {"school_name": "Central Oklahoma", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://bronchoathletics.com"},
    {"school_name": "Northeastern St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://nsuriverhawks.com"},
    {"school_name": "Washburn", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://wusports.com"},
    {"school_name": "Missouri Western", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://gogriffons.com"},
    {"school_name": "Fort Hays St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://fhsuathletics.com"},
    {"school_name": "Missouri Southern", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://mssuathletics.com"},
    {"school_name": "Nebraska Kearney", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://lopers.com"},
    {"school_name": "Lindenwood", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://lindenwoodlions.com"},
    {"school_name": "Rogers St.", "division": "D2", "conference": "MIAA", "athletics_base_url": "https://rsuhillcats.com"},

    # ── GAC (Great American Conference) ───────────────────────────
    {"school_name": "Arkansas Tech", "division": "D2", "conference": "GAC", "athletics_base_url": "https://arkansastechsports.com"},
    {"school_name": "Harding", "division": "D2", "conference": "GAC", "athletics_base_url": "https://hardingsports.com"},
    {"school_name": "Henderson St.", "division": "D2", "conference": "GAC", "athletics_base_url": "https://hendersonreddies.com"},
    {"school_name": "Ouachita Baptist", "division": "D2", "conference": "GAC", "athletics_base_url": "https://obutigers.com"},
    {"school_name": "Southeastern Oklahoma", "division": "D2", "conference": "GAC", "athletics_base_url": "https://savagesports.com"},
    {"school_name": "Southern Arkansas", "division": "D2", "conference": "GAC", "athletics_base_url": "https://muleriderathletics.com"},
    {"school_name": "Southern Nazarene", "division": "D2", "conference": "GAC", "athletics_base_url": "https://snuathletics.com"},
    {"school_name": "Southwestern Oklahoma", "division": "D2", "conference": "GAC", "athletics_base_url": "https://swosuathletics.com"},
    {"school_name": "East Central", "division": "D2", "conference": "GAC", "athletics_base_url": "https://ectigerathletics.com"},
    {"school_name": "Oklahoma Baptist", "division": "D2", "conference": "GAC", "athletics_base_url": "https://obubison.com"},
    {"school_name": "Northwestern Oklahoma", "division": "D2", "conference": "GAC", "athletics_base_url": "https://nwosurangers.com"},
    {"school_name": "Arkansas-Monticello", "division": "D2", "conference": "GAC", "athletics_base_url": "https://uamboilweevils.com"},

    # ── LSC (Lone Star Conference) ────────────────────────────────
    {"school_name": "Angelo St.", "division": "D2", "conference": "LSC", "athletics_base_url": "https://angelosports.com"},
    {"school_name": "West Texas A&M", "division": "D2", "conference": "LSC", "athletics_base_url": "https://gobuffsgo.com"},
    {"school_name": "Lubbock Christian", "division": "D2", "conference": "LSC", "athletics_base_url": "https://lcuchaps.com"},
    {"school_name": "Texas A&M-Kingsville", "division": "D2", "conference": "LSC", "athletics_base_url": "https://javelinaathletics.com"},
    {"school_name": "Tarleton St.", "division": "D2", "conference": "LSC", "athletics_base_url": "https://tarletonsports.com"},
    {"school_name": "Cameron", "division": "D2", "conference": "LSC", "athletics_base_url": "https://cameronaggieathletics.com"},
    {"school_name": "Eastern New Mexico", "division": "D2", "conference": "LSC", "athletics_base_url": "https://goenmugranados.com"},
    {"school_name": "Western New Mexico", "division": "D2", "conference": "LSC", "athletics_base_url": "https://wnmuathletics.com"},
    {"school_name": "UT Permian Basin", "division": "D2", "conference": "LSC", "athletics_base_url": "https://utpbfalcons.com"},
    {"school_name": "St. Mary's (TX)", "division": "D2", "conference": "LSC", "athletics_base_url": "https://stmarytx.edu/athletics"},
    {"school_name": "Texas A&M International", "division": "D2", "conference": "LSC", "athletics_base_url": "https://tamiu.edu/athletics"},
    {"school_name": "UT Tyler", "division": "D2", "conference": "LSC", "athletics_base_url": "https://uttylerpatriots.com"},
    {"school_name": "Dallas Baptist", "division": "D2", "conference": "LSC", "athletics_base_url": "https://dbupatriots.com"},
    {"school_name": "St. Edward's", "division": "D2", "conference": "LSC", "athletics_base_url": "https://gohilltoppers.com"},
    {"school_name": "Texas-Tyler", "division": "D2", "conference": "LSC", "athletics_base_url": "https://uttylerpatriots.com"},

    # ── RMAC (Rocky Mountain Athletic Conference) ─────────────────
    {"school_name": "Colorado Mesa", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://cmumavericks.com"},
    {"school_name": "Colorado School of Mines", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://minesathletics.com"},
    {"school_name": "Regis (CO)", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://regisrangers.com"},
    {"school_name": "Colorado Christian", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://ccucougars.com"},
    {"school_name": "Metro St.", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://msudroadrunners.com"},
    {"school_name": "Adams St.", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://asugrizzlies.com"},
    {"school_name": "Colorado St.-Pueblo", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://gothunderwolves.com"},
    {"school_name": "New Mexico Highlands", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://nmhucowboys.com"},
    {"school_name": "Western Colorado", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://mountaineersathletics.com"},
    {"school_name": "Fort Lewis", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://goskyhawks.com"},
    {"school_name": "Black Hills St.", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://bhsuyellowjackets.com"},
    {"school_name": "SD School of Mines", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://hardrockerathletics.com"},
    {"school_name": "Chadron St.", "division": "D2", "conference": "RMAC", "athletics_base_url": "https://csceagles.com"},

    # ── CCAA (California Collegiate Athletic Association) ─────────
    {"school_name": "Cal Poly Pomona", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://broncoathletics.com"},
    {"school_name": "Chico St.", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://chicowildcats.com"},
    {"school_name": "Cal St. Dominguez Hills", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://csudhtorosathletics.com"},
    {"school_name": "Cal St. San Bernardino", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://caborathletics.com"},
    {"school_name": "Cal St. LA", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://calstatela.com/athletics"},
    {"school_name": "Cal St. Monterey Bay", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://otterathletics.com"},
    {"school_name": "Cal St. East Bay", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://caborathletics.com"},
    {"school_name": "Sonoma St.", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://ssuseawolves.com"},
    {"school_name": "Stanislaus St.", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://csustanwarriors.com"},
    {"school_name": "San Francisco St.", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://sfstategators.com"},
    {"school_name": "Humboldt St.", "division": "D2", "conference": "CCAA", "athletics_base_url": "https://hsujacks.com"},

    # ── PacWest (Pacific West Conference) ─────────────────────────
    {"school_name": "Point Loma", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://plnusealions.com"},
    {"school_name": "Azusa Pacific", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://apucougars.com"},
    {"school_name": "Biola", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://biolaeagles.com"},
    {"school_name": "Concordia Irvine", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://cuieagles.com"},
    {"school_name": "Fresno Pacific", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://fpuathletics.com"},
    {"school_name": "Hawaii Hilo", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://hiloathletics.com"},
    {"school_name": "Hawaii Pacific", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://hpusharks.com"},
    {"school_name": "Academy of Art", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://artusports.com"},
    {"school_name": "Dominican (CA)", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://dominicanpenguins.com"},
    {"school_name": "Holy Names", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://hnuhawks.com"},
    {"school_name": "Chaminade", "division": "D2", "conference": "PacWest", "athletics_base_url": "https://goswords.com"},

    # ── GNAC (Great Northwest Athletic Conference) ────────────────
    {"school_name": "Western Oregon", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://wouwolves.com"},
    {"school_name": "Central Washington", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://wildcatsports.com"},
    {"school_name": "Western Washington", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://wwuvikings.com"},
    {"school_name": "Simon Fraser", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://sfuclan.com"},
    {"school_name": "Saint Martin's", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://stmartinsaints.com"},
    {"school_name": "Montana St. Billings", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://msbsports.com"},
    {"school_name": "Northwest Nazarene", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://nnusports.com"},
    {"school_name": "Concordia (OR)", "division": "D2", "conference": "GNAC", "athletics_base_url": "https://gocucavaliers.com"},

    # ── MEC (Mountain East Conference) ────────────────────────────
    {"school_name": "Charleston (WV)", "division": "D2", "conference": "MEC", "athletics_base_url": "https://ucgoldeneagles.com"},
    {"school_name": "Concord", "division": "D2", "conference": "MEC", "athletics_base_url": "https://concordathletics.com"},
    {"school_name": "Fairmont St.", "division": "D2", "conference": "MEC", "athletics_base_url": "https://fightingfalcons.com"},
    {"school_name": "Glenville St.", "division": "D2", "conference": "MEC", "athletics_base_url": "https://gscpioneers.com"},
    {"school_name": "Notre Dame (OH)", "division": "D2", "conference": "MEC", "athletics_base_url": "https://nducfalcons.com"},
    {"school_name": "Salem (WV)", "division": "D2", "conference": "MEC", "athletics_base_url": "https://salemtigers.com"},
    {"school_name": "Shepherd", "division": "D2", "conference": "MEC", "athletics_base_url": "https://shepherdrams.com"},
    {"school_name": "WV Wesleyan", "division": "D2", "conference": "MEC", "athletics_base_url": "https://wvwcathletics.com"},
    {"school_name": "West Liberty", "division": "D2", "conference": "MEC", "athletics_base_url": "https://westlibertyathletics.com"},
    {"school_name": "West Virginia St.", "division": "D2", "conference": "MEC", "athletics_base_url": "https://wvstateyellowjackets.com"},
    {"school_name": "Wheeling", "division": "D2", "conference": "MEC", "athletics_base_url": "https://wheelingcardinals.com"},
    {"school_name": "Frostburg St.", "division": "D2", "conference": "MEC", "athletics_base_url": "https://frostburgsports.com"},
    {"school_name": "UVA Wise", "division": "D2", "conference": "MEC", "athletics_base_url": "https://uvawisecavaliers.com"},

    # ── DII Independents ──────────────────────────────────────────
    {"school_name": "Bellarmine", "division": "D2", "conference": "DII Independent", "athletics_base_url": "https://bellarmineknights.com"},


    # ═══════════════════════════════════════════════════════════════
    # D3 Schools (421 schools)
    # ═══════════════════════════════════════════════════════════════

    # AMCC
    {"school_name": "Alfred State", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://alfredstateathletics.com"},
    {"school_name": "D'Youville", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://dyouvilleathletics.com"},
    {"school_name": "Franciscan", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://fubarons.com"},
    {"school_name": "Hilbert", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://hilbertathletics.com"},
    {"school_name": "La Roche", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://larocheredhawks.com"},
    {"school_name": "Medaille", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://medailleathletics.com"},
    {"school_name": "Mount Aloysius", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://mountaloysiusathletics.com"},
    {"school_name": "Penn State Altoona", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://altoonaathletics.com"},
    {"school_name": "Penn State Behrend", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://behrendlions.com"},
    {"school_name": "Pitt-Bradford", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://pittbradfordsports.com"},
    {"school_name": "Pitt-Greensburg", "division": "D3", "conference": "AMCC", "athletics_base_url": "https://pittgreensburgathletics.com"},

    # ASC
    {"school_name": "Concordia Texas", "division": "D3", "conference": "ASC", "athletics_base_url": "https://ctxathletics.com"},
    {"school_name": "East Texas Baptist", "division": "D3", "conference": "ASC", "athletics_base_url": "https://etbutigers.com"},
    {"school_name": "Hardin-Simmons", "division": "D3", "conference": "ASC", "athletics_base_url": "https://hsutx.edu/athletics"},
    {"school_name": "Howard Payne", "division": "D3", "conference": "ASC", "athletics_base_url": "https://hpuathletics.com"},
    {"school_name": "LeTourneau", "division": "D3", "conference": "ASC", "athletics_base_url": "https://letuyellowjackets.com"},
    {"school_name": "Mary Hardin-Baylor", "division": "D3", "conference": "ASC", "athletics_base_url": "https://umhbathletics.com"},
    {"school_name": "McMurry", "division": "D3", "conference": "ASC", "athletics_base_url": "https://mcmurrysports.com"},
    {"school_name": "Ozarks (AR)", "division": "D3", "conference": "ASC", "athletics_base_url": "https://ozarkseagles.com"},
    {"school_name": "Sul Ross State", "division": "D3", "conference": "ASC", "athletics_base_url": "https://srsathletics.com"},
    {"school_name": "UT Dallas", "division": "D3", "conference": "ASC", "athletics_base_url": "https://utdcomets.com"},
    {"school_name": "UT Tyler", "division": "D3", "conference": "ASC", "athletics_base_url": "https://uttylerpatriots.com"},

    # American Rivers
    {"school_name": "Buena Vista", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://bvathletics.com"},
    {"school_name": "Central (IA)", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://central.edu/athletics"},
    {"school_name": "Coe", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://coekohawks.com"},
    {"school_name": "Dubuque", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://dbqspartans.com"},
    {"school_name": "Loras", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://lorasduhawks.com"},
    {"school_name": "Luther", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://luthernorse.com"},
    {"school_name": "Nebraska Wesleyan", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://nwusports.com"},
    {"school_name": "Simpson", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://simpsonathletics.com"},
    {"school_name": "Upper Iowa", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://uiupeacocks.com"},
    {"school_name": "Wartburg", "division": "D3", "conference": "American Rivers", "athletics_base_url": "https://wartburgsports.com"},

    # Atlantic East
    {"school_name": "Cabrini", "division": "D3", "conference": "Atlantic East", "athletics_base_url": "https://cabriniathletics.com"},
    {"school_name": "Gwynedd Mercy", "division": "D3", "conference": "Atlantic East", "athletics_base_url": "https://gmercygriffinsat.com"},
    {"school_name": "Holy Family", "division": "D3", "conference": "Atlantic East", "athletics_base_url": "https://holyfamilytigers.com"},

    # CAC
    {"school_name": "Christopher Newport", "division": "D3", "conference": "CAC", "athletics_base_url": "https://cnucaptains.com"},
    {"school_name": "Frostburg State", "division": "D3", "conference": "CAC", "athletics_base_url": "https://frostburgathletics.com"},
    {"school_name": "Mary Washington", "division": "D3", "conference": "CAC", "athletics_base_url": "https://umweagles.com"},
    {"school_name": "Marymount (VA)", "division": "D3", "conference": "CAC", "athletics_base_url": "https://marymountsaints.com"},
    {"school_name": "Salisbury", "division": "D3", "conference": "CAC", "athletics_base_url": "https://salisburysports.com"},
    {"school_name": "Southern Virginia", "division": "D3", "conference": "CAC", "athletics_base_url": "https://svuknights.com"},
    {"school_name": "St. Mary's (MD)", "division": "D3", "conference": "CAC", "athletics_base_url": "https://smcmsports.com"},
    {"school_name": "York (PA)", "division": "D3", "conference": "CAC", "athletics_base_url": "https://ycp.edu/athletics"},

    # CCC
    {"school_name": "Curry", "division": "D3", "conference": "CCC", "athletics_base_url": "https://curryathletics.com"},
    {"school_name": "Endicott", "division": "D3", "conference": "CCC", "athletics_base_url": "https://endicottathletics.com"},
    {"school_name": "Gordon", "division": "D3", "conference": "CCC", "athletics_base_url": "https://gordonathletics.com"},
    {"school_name": "Nichols", "division": "D3", "conference": "CCC", "athletics_base_url": "https://nicholsathletics.com"},
    {"school_name": "Roger Williams", "division": "D3", "conference": "CCC", "athletics_base_url": "https://rwuhawks.com"},
    {"school_name": "Salve Regina", "division": "D3", "conference": "CCC", "athletics_base_url": "https://salveathletics.com"},
    {"school_name": "UNE", "division": "D3", "conference": "CCC", "athletics_base_url": "https://uneathletics.com"},
    {"school_name": "Wentworth", "division": "D3", "conference": "CCC", "athletics_base_url": "https://wentworthathletics.com"},
    {"school_name": "Western New England", "division": "D3", "conference": "CCC", "athletics_base_url": "https://wnegoldenbears.com"},

    # CCIW
    {"school_name": "Augustana (IL)", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://goaugie.com"},
    {"school_name": "Carroll (WI)", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://carrollathletics.com"},
    {"school_name": "Carthage", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://carthagesports.com"},
    {"school_name": "Elmhurst", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://elmhurstsports.com"},
    {"school_name": "Illinois Wesleyan", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://iwusports.com"},
    {"school_name": "Millikin", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://millikinbigblue.com"},
    {"school_name": "North Central (IL)", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://northcentralcardinals.com"},
    {"school_name": "North Park", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://northparkvikings.com"},
    {"school_name": "Wheaton (IL)", "division": "D3", "conference": "CCIW", "athletics_base_url": "https://wheatonthunder.com"},

    # CSAC
    {"school_name": "Cairn", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://cairnhighlanders.com"},
    {"school_name": "Cedar Crest", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://cedarcrestathletics.com"},
    {"school_name": "Centenary (NJ)", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://centenarygators.com"},
    {"school_name": "Clarks Summit", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://csudefenders.com"},
    {"school_name": "Immaculata", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://immaculataathletics.com"},
    {"school_name": "Keystone", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://kcgiants.com"},
    {"school_name": "Marywood", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://marywoodpacers.com"},
    {"school_name": "Neumann", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://neumannathletics.com"},
    {"school_name": "Notre Dame (MD)", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://ndmathletics.com"},
    {"school_name": "Rosemont", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://rosemontathletics.com"},
    {"school_name": "Wilson", "division": "D3", "conference": "CSAC", "athletics_base_url": "https://wilsonphoenix.com"},

    # CUNYAC
    {"school_name": "Baruch", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://baruchathletics.com"},
    {"school_name": "Brooklyn College", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://brooklyncollegeathletics.com"},
    {"school_name": "CCNY", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://ccnyathletics.com"},
    {"school_name": "City Tech", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://citytechathletics.com"},
    {"school_name": "Hunter", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://huntercollegeathletics.com"},
    {"school_name": "John Jay", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://johnjayathletics.com"},
    {"school_name": "Lehman", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://lehmanathletics.com"},
    {"school_name": "Medgar Evers", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://mecathletics.com"},
    {"school_name": "Staten Island", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://csidolphins.com"},
    {"school_name": "York College (NY)", "division": "D3", "conference": "CUNYAC", "athletics_base_url": "https://yorkathletics.com"},

    # Centennial
    {"school_name": "Bryn Athyn", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://brynathletics.com"},
    {"school_name": "Dickinson", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://dickinsonathletics.com"},
    {"school_name": "Franklin & Marshall", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://godiplomats.com"},
    {"school_name": "Gettysburg", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://gettysburgsports.com"},
    {"school_name": "Haverford", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://haverfordathletics.com"},
    {"school_name": "Johns Hopkins", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://hopkinssports.com"},
    {"school_name": "McDaniel", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://mcdanielathletics.com"},
    {"school_name": "Muhlenberg", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://muhlenbergsports.com"},
    {"school_name": "Swarthmore", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://swarthmoresports.com"},
    {"school_name": "Ursinus", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://ursinusathletics.com"},
    {"school_name": "Washington College", "division": "D3", "conference": "Centennial", "athletics_base_url": "https://washingtoncollegesports.com"},

    # Empire 8
    {"school_name": "Alfred", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://alfredathletics.com"},
    {"school_name": "Elmira", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://goelmira.com"},
    {"school_name": "Hartwick", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://hartwickathletics.com"},
    {"school_name": "Houghton", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://houghtonathletics.com"},
    {"school_name": "Nazareth", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://nazathletics.com"},
    {"school_name": "Sage", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://sageathletics.com"},
    {"school_name": "St. John Fisher", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://sjfcathletics.com"},
    {"school_name": "Stevens", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://stevensathletics.com"},
    {"school_name": "Utica", "division": "D3", "conference": "Empire 8", "athletics_base_url": "https://uticapioneers.com"},

    # GNAC
    {"school_name": "Albertus Magnus", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://albertusathletics.com"},
    {"school_name": "Anna Maria", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://amcatssports.com"},
    {"school_name": "Colby-Sawyer", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://colbysawyerathletics.com"},
    {"school_name": "Dean", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://deanathletics.com"},
    {"school_name": "Eastern Nazarene", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://enclions.com"},
    {"school_name": "Elms", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://elmsblazers.com"},
    {"school_name": "Johnson & Wales", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://jwuathletics.com"},
    {"school_name": "Lasell", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://golaselllasers.com"},
    {"school_name": "Mitchell", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://mitchellathletics.com"},
    {"school_name": "New England College", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://necpilgrims.com"},
    {"school_name": "Norwich", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://norwichathletics.com"},
    {"school_name": "Suffolk", "division": "D3", "conference": "GNAC", "athletics_base_url": "https://suffolkrams.com"},

    # Heartland
    {"school_name": "Anderson (IN)", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://andersonravens.com"},
    {"school_name": "Bluffton", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://blufftonbeavers.com"},
    {"school_name": "Defiance", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://defianceathletics.com"},
    {"school_name": "Earlham", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://earlhamathletics.com"},
    {"school_name": "Franklin", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://franklingrizzlies.com"},
    {"school_name": "Hanover", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://hanoverathletics.com"},
    {"school_name": "Manchester", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://manchesterspartans.com"},
    {"school_name": "Mount St. Joseph", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://msjlions.com"},
    {"school_name": "Rose-Hulman", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://rosehulmanathletics.com"},
    {"school_name": "Transylvania", "division": "D3", "conference": "Heartland", "athletics_base_url": "https://transyathletics.com"},

    # Independent
    {"school_name": "Maine Maritime", "division": "D3", "conference": "Independent", "athletics_base_url": "https://mainemaritime.edu/athletics"},
    {"school_name": "Merchant Marine", "division": "D3", "conference": "Independent", "athletics_base_url": "https://usmmasports.com"},
    {"school_name": "Southern Vermont", "division": "D3", "conference": "Independent", "athletics_base_url": "https://svceagles.com"},
    {"school_name": "Thomas (ME)", "division": "D3", "conference": "Independent", "athletics_base_url": "https://thomasterriers.com"},

    # Landmark
    {"school_name": "Catholic", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://cuacardinals.com"},
    {"school_name": "Drew", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://drewrangers.com"},
    {"school_name": "Elizabethtown", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://etownbluejays.com"},
    {"school_name": "Goucher", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://goucherathletics.com"},
    {"school_name": "Juniata", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://juniataeagles.com"},
    {"school_name": "Moravian", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://moravianathletics.com"},
    {"school_name": "Scranton", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://goroyal.com"},
    {"school_name": "Susquehanna", "division": "D3", "conference": "Landmark", "athletics_base_url": "https://susquathletics.com"},

    # Liberty League
    {"school_name": "Bard", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://bardathletics.com"},
    {"school_name": "Clarkson", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://clarksonathletics.com"},
    {"school_name": "Hobart", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://hwsathletics.com"},
    {"school_name": "Ithaca", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://ithacabombers.com"},
    {"school_name": "RIT", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://ritathletics.com"},
    {"school_name": "RPI", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://rpiathletics.com"},
    {"school_name": "Rensselaer", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://rpiathletics.com"},
    {"school_name": "Rochester (NY)", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://uofrathletics.com"},
    {"school_name": "Skidmore", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://skidmoreathletics.com"},
    {"school_name": "St. Lawrence", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://saintsathletics.com"},
    {"school_name": "Union (NY)", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://unionathletics.com"},
    {"school_name": "Vassar", "division": "D3", "conference": "Liberty League", "athletics_base_url": "https://vassarathletics.com"},

    # Little East
    {"school_name": "Eastern Connecticut", "division": "D3", "conference": "Little East", "athletics_base_url": "https://easternctwarriors.com"},
    {"school_name": "Keene State", "division": "D3", "conference": "Little East", "athletics_base_url": "https://keeneowls.com"},
    {"school_name": "Mass. Maritime", "division": "D3", "conference": "Little East", "athletics_base_url": "https://mmabucs.com"},
    {"school_name": "Plymouth State", "division": "D3", "conference": "Little East", "athletics_base_url": "https://plymouthstateathletics.com"},
    {"school_name": "Rhode Island College", "division": "D3", "conference": "Little East", "athletics_base_url": "https://ricathletics.com"},
    {"school_name": "Southern Maine", "division": "D3", "conference": "Little East", "athletics_base_url": "https://southernmainehuskies.com"},
    {"school_name": "UMass Boston", "division": "D3", "conference": "Little East", "athletics_base_url": "https://umbathletics.com"},
    {"school_name": "UMass Dartmouth", "division": "D3", "conference": "Little East", "athletics_base_url": "https://corsairathletics.com"},
    {"school_name": "Western Connecticut", "division": "D3", "conference": "Little East", "athletics_base_url": "https://wcsuathletics.com"},

    # MAC
    {"school_name": "Albright", "division": "D3", "conference": "MAC", "athletics_base_url": "https://albrightlions.com"},
    {"school_name": "Alvernia", "division": "D3", "conference": "MAC", "athletics_base_url": "https://alverniaathletics.com"},
    {"school_name": "Arcadia", "division": "D3", "conference": "MAC", "athletics_base_url": "https://arcadiaknights.com"},
    {"school_name": "DeSales", "division": "D3", "conference": "MAC", "athletics_base_url": "https://desalesbulldogs.com"},
    {"school_name": "Delaware Valley", "division": "D3", "conference": "MAC", "athletics_base_url": "https://dvuathletics.com"},
    {"school_name": "Eastern", "division": "D3", "conference": "MAC", "athletics_base_url": "https://goeueagles.com"},
    {"school_name": "Fairleigh Dickinson-Florham", "division": "D3", "conference": "MAC", "athletics_base_url": "https://fdudevilsathletics.com"},
    {"school_name": "Hood", "division": "D3", "conference": "MAC", "athletics_base_url": "https://hoodathletics.com"},
    {"school_name": "King's (PA)", "division": "D3", "conference": "MAC", "athletics_base_url": "https://kingsmonarchs.com"},
    {"school_name": "Lebanon Valley", "division": "D3", "conference": "MAC", "athletics_base_url": "https://lvcathletics.com"},
    {"school_name": "Lycoming", "division": "D3", "conference": "MAC", "athletics_base_url": "https://lycomingwarriors.com"},
    {"school_name": "Misericordia", "division": "D3", "conference": "MAC", "athletics_base_url": "https://misericordiacougars.com"},
    {"school_name": "Stevenson", "division": "D3", "conference": "MAC", "athletics_base_url": "https://stevensonathletics.com"},
    {"school_name": "Widener", "division": "D3", "conference": "MAC", "athletics_base_url": "https://widenerathletics.com"},
    {"school_name": "Wilkes", "division": "D3", "conference": "MAC", "athletics_base_url": "https://wilkesathletics.com"},

    # MASCAC
    {"school_name": "Bridgewater State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://bsubears.com"},
    {"school_name": "Fitchburg State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://fitchburgathletics.com"},
    {"school_name": "Framingham State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://framinghamrams.com"},
    {"school_name": "MCLA", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://mclatrailblazers.com"},
    {"school_name": "Salem State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://salemstatevikings.com"},
    {"school_name": "Westfield State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://westfieldstateowls.com"},
    {"school_name": "Worcester State", "division": "D3", "conference": "MASCAC", "athletics_base_url": "https://worcesterstateathletics.com"},

    # MIAA
    {"school_name": "Adrian", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://adrianbulldogs.com"},
    {"school_name": "Albion", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://albionbritons.com"},
    {"school_name": "Alma", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://almascots.com"},
    {"school_name": "Calvin", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://calvinknights.com"},
    {"school_name": "Hope", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://hope.edu/athletics"},
    {"school_name": "Kalamazoo", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://kzoo.edu/athletics"},
    {"school_name": "Olivet", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://olivetathletics.com"},
    {"school_name": "Saint Mary's (MI)", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://smarycardinals.com"},
    {"school_name": "Trine", "division": "D3", "conference": "MIAA", "athletics_base_url": "https://trinethunder.com"},

    # MIAC
    {"school_name": "Augsburg", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://augsburgauggies.com"},
    {"school_name": "Bethel (MN)", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://bethelroyals.com"},
    {"school_name": "Carleton", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://carletonknights.com"},
    {"school_name": "Concordia (MN)", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://cobberathletics.com"},
    {"school_name": "Concordia Chicago", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://cuccougars.com"},
    {"school_name": "Gustavus Adolphus", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://gustavusathletics.com"},
    {"school_name": "Hamline", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://hamlineathletics.com"},
    {"school_name": "Macalester", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://macalesterathletics.com"},
    {"school_name": "Minnesota Morris", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://morriscougars.com"},
    {"school_name": "Saint Mary's (MN)", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://smucardinals.com"},
    {"school_name": "St. John's (MN)", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://gojohnnies.com"},
    {"school_name": "St. Olaf", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://stolaf.edu/athletics"},
    {"school_name": "St. Thomas (MN)", "division": "D3", "conference": "MIAC", "athletics_base_url": "https://tommiesports.com"},

    # Midwest
    {"school_name": "Beloit", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://beloitbucs.com"},
    {"school_name": "Cornell College", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://cornellrams.com"},
    {"school_name": "Grinnell", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://grinnellpioneers.com"},
    {"school_name": "Illinois College", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://icblueboys.com"},
    {"school_name": "Knox", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://knoxprairefire.com"},
    {"school_name": "Lake Forest", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://goforesters.com"},
    {"school_name": "Lawrence", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://lawrencevikings.com"},
    {"school_name": "Monmouth (IL)", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://monmouthscots.com"},
    {"school_name": "Ripon", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://riponathletics.com"},
    {"school_name": "St. Norbert", "division": "D3", "conference": "Midwest", "athletics_base_url": "https://sncsports.com"},

    # NAC
    {"school_name": "Castleton", "division": "D3", "conference": "NAC", "athletics_base_url": "https://castletonspartans.com"},
    {"school_name": "Green Mountain", "division": "D3", "conference": "NAC", "athletics_base_url": "https://greenmountainathletics.com"},
    {"school_name": "Husson", "division": "D3", "conference": "NAC", "athletics_base_url": "https://hussonathletics.com"},
    {"school_name": "Johnson State", "division": "D3", "conference": "NAC", "athletics_base_url": "https://jscathletics.com"},
    {"school_name": "Lyndon State", "division": "D3", "conference": "NAC", "athletics_base_url": "https://lyndonathletics.com"},
    {"school_name": "Maine-Farmington", "division": "D3", "conference": "NAC", "athletics_base_url": "https://umfathletics.com"},
    {"school_name": "Maine-Presque Isle", "division": "D3", "conference": "NAC", "athletics_base_url": "https://umpiathletics.com"},
    {"school_name": "Northern Vermont-Johnson", "division": "D3", "conference": "NAC", "athletics_base_url": "https://nvuathletics.com"},
    {"school_name": "Thomas College", "division": "D3", "conference": "NAC", "athletics_base_url": "https://thomasterriers.com"},

    # NACC
    {"school_name": "Aurora", "division": "D3", "conference": "NACC", "athletics_base_url": "https://auroraspartans.com"},
    {"school_name": "Benedictine (IL)", "division": "D3", "conference": "NACC", "athletics_base_url": "https://beneagles.com"},
    {"school_name": "Concordia (WI)", "division": "D3", "conference": "NACC", "athletics_base_url": "https://cufalcons.com"},
    {"school_name": "Dominican (IL)", "division": "D3", "conference": "NACC", "athletics_base_url": "https://dustars.com"},
    {"school_name": "Edgewood", "division": "D3", "conference": "NACC", "athletics_base_url": "https://edgewoodathletics.com"},
    {"school_name": "Lakeland", "division": "D3", "conference": "NACC", "athletics_base_url": "https://lakelandmuskies.com"},
    {"school_name": "MSOE", "division": "D3", "conference": "NACC", "athletics_base_url": "https://msoeathletics.com"},
    {"school_name": "Marian (WI)", "division": "D3", "conference": "NACC", "athletics_base_url": "https://marianathletics.com"},
    {"school_name": "Rockford", "division": "D3", "conference": "NACC", "athletics_base_url": "https://rockfordregents.com"},

    # NCAC
    {"school_name": "Allegheny", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://alleghenygators.com"},
    {"school_name": "DePauw", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://depauwtigers.com"},
    {"school_name": "Denison", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://denisonbigred.com"},
    {"school_name": "Hiram", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://hiramathletics.com"},
    {"school_name": "Kenyon", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://kenyonlords.com"},
    {"school_name": "Oberlin", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://oberlinyeomen.com"},
    {"school_name": "Ohio Wesleyan", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://battlingbishops.com"},
    {"school_name": "Wabash", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://wabash.edu/athletics"},
    {"school_name": "Wittenberg", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://wittenbergtigers.com"},
    {"school_name": "Wooster", "division": "D3", "conference": "NCAC", "athletics_base_url": "https://woosterathletics.com"},

    # NEAC
    {"school_name": "Cazenovia", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://cazathletics.com"},
    {"school_name": "Gallaudet", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://gallaudetathletics.com"},
    {"school_name": "Keuka", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://keukaathletics.com"},
    {"school_name": "Lancaster Bible", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://lbcathletics.com"},
    {"school_name": "Morrisville State", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://msvmustangs.com"},
    {"school_name": "Penn State Abington", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://abingtonsports.com"},
    {"school_name": "Penn State Berks", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://berksnittanylions.com"},
    {"school_name": "Penn State Harrisburg", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://harrisburgathletics.com"},
    {"school_name": "SUNY Canton", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://cantonroos.com"},
    {"school_name": "SUNY Cobleskill", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://cobleskillsports.com"},
    {"school_name": "SUNY Delhi", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://delhisports.com"},
    {"school_name": "SUNY Poly", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://sunypoly.edu/athletics"},
    {"school_name": "Wells", "division": "D3", "conference": "NEAC", "athletics_base_url": "https://wellsathletics.com"},

    # NESCAC
    {"school_name": "Amherst", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://amherstmammoths.com"},
    {"school_name": "Bates", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://gobatesbobcats.com"},
    {"school_name": "Bowdoin", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://bowdoinpolarbears.com"},
    {"school_name": "Colby", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://colbymules.com"},
    {"school_name": "Connecticut College", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://camelathletics.com"},
    {"school_name": "Hamilton", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://athletics.hamilton.edu"},
    {"school_name": "Middlebury", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://middleburyathletics.com"},
    {"school_name": "Trinity (CT)", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://bantamsports.com"},
    {"school_name": "Tufts", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://gotuftsjumbos.com"},
    {"school_name": "Wesleyan", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://athletics.wesleyan.edu"},
    {"school_name": "Wesleyan (CT)", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://athletics.wesleyan.edu"},
    {"school_name": "Williams", "division": "D3", "conference": "NESCAC", "athletics_base_url": "https://ephsports.williams.edu"},

    # NEWMAC
    {"school_name": "Babson", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://babsonathletics.com"},
    {"school_name": "Clark (MA)", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://clarkathletics.com"},
    {"school_name": "Coast Guard", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://coastguardbears.com"},
    {"school_name": "Emerson", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://emersonlions.com"},
    {"school_name": "MIT", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://mitathletics.com"},
    {"school_name": "Springfield", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://springfieldcollege.edu/athletics"},
    {"school_name": "WPI", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://athletics.wpi.edu"},
    {"school_name": "Wheaton (MA)", "division": "D3", "conference": "NEWMAC", "athletics_base_url": "https://wheatoncollegelyons.com"},

    # NJAC
    {"school_name": "Kean", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://keancougars.com"},
    {"school_name": "MSU New Jersey", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://msaborpathletics.com"},
    {"school_name": "Montclair State", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://montclairathletics.com"},
    {"school_name": "New Jersey City", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://njcugothicknights.com"},
    {"school_name": "Ramapo", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://ramapoathletics.com"},
    {"school_name": "Rowan", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://rowanprofs.com"},
    {"school_name": "Rutgers-Camden", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://rutgerscamdenathletics.com"},
    {"school_name": "Rutgers-Newark", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://rutgersnewark.com"},
    {"school_name": "Stockton", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://stocktonathletics.com"},
    {"school_name": "TCNJ", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://tcnjlions.com"},
    {"school_name": "William Paterson", "division": "D3", "conference": "NJAC", "athletics_base_url": "https://wpunj.com"},

    # NWC
    {"school_name": "George Fox", "division": "D3", "conference": "NWC", "athletics_base_url": "https://georgefoxbruins.com"},
    {"school_name": "Lewis & Clark", "division": "D3", "conference": "NWC", "athletics_base_url": "https://lcpioneers.com"},
    {"school_name": "Linfield", "division": "D3", "conference": "NWC", "athletics_base_url": "https://linfieldsports.com"},
    {"school_name": "Pacific (OR)", "division": "D3", "conference": "NWC", "athletics_base_url": "https://goboxers.com"},
    {"school_name": "Pacific Lutheran", "division": "D3", "conference": "NWC", "athletics_base_url": "https://golutes.com"},
    {"school_name": "Puget Sound", "division": "D3", "conference": "NWC", "athletics_base_url": "https://loggerathletics.com"},
    {"school_name": "Whitman", "division": "D3", "conference": "NWC", "athletics_base_url": "https://whitmanathletics.com"},
    {"school_name": "Whitworth", "division": "D3", "conference": "NWC", "athletics_base_url": "https://whitworthpirates.com"},
    {"school_name": "Willamette", "division": "D3", "conference": "NWC", "athletics_base_url": "https://willamettesports.com"},

    # OAC
    {"school_name": "Baldwin Wallace", "division": "D3", "conference": "OAC", "athletics_base_url": "https://bwyellowjackets.com"},
    {"school_name": "Capital", "division": "D3", "conference": "OAC", "athletics_base_url": "https://capitalathletics.com"},
    {"school_name": "Heidelberg", "division": "D3", "conference": "OAC", "athletics_base_url": "https://bergbergies.com"},
    {"school_name": "John Carroll", "division": "D3", "conference": "OAC", "athletics_base_url": "https://jcusports.com"},
    {"school_name": "Marietta", "division": "D3", "conference": "OAC", "athletics_base_url": "https://mariettapioneers.com"},
    {"school_name": "Mount Union", "division": "D3", "conference": "OAC", "athletics_base_url": "https://mountunionathletics.com"},
    {"school_name": "Muskingum", "division": "D3", "conference": "OAC", "athletics_base_url": "https://muskingumfighting.com"},
    {"school_name": "Ohio Dominican", "division": "D3", "conference": "OAC", "athletics_base_url": "https://ohiodominicansports.com"},
    {"school_name": "Ohio Northern", "division": "D3", "conference": "OAC", "athletics_base_url": "https://onusports.com"},
    {"school_name": "Otterbein", "division": "D3", "conference": "OAC", "athletics_base_url": "https://otterbeincardinals.com"},
    {"school_name": "Wilmington (OH)", "division": "D3", "conference": "OAC", "athletics_base_url": "https://wilmingtonathletics.com"},

    # ODAC
    {"school_name": "Averett", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://averettcougars.com"},
    {"school_name": "Bridgewater (VA)", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://bridgewatereagles.com"},
    {"school_name": "Eastern Mennonite", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://emuroyals.com"},
    {"school_name": "Ferrum", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://ferrumpanthers.com"},
    {"school_name": "Guilford", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://guilfordquakers.com"},
    {"school_name": "Hampden-Sydney", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://hsctigers.com"},
    {"school_name": "Lynchburg", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://lynchburgsports.com"},
    {"school_name": "Randolph", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://randolphwildcats.com"},
    {"school_name": "Randolph-Macon", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://rmcathletics.com"},
    {"school_name": "Roanoke", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://roanokemaroons.com"},
    {"school_name": "Shenandoah", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://suhornets.com"},
    {"school_name": "Virginia Wesleyan", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://vwuathletics.com"},
    {"school_name": "Washington and Lee", "division": "D3", "conference": "ODAC", "athletics_base_url": "https://generalssports.com"},

    # PAC
    {"school_name": "Bethany (WV)", "division": "D3", "conference": "PAC", "athletics_base_url": "https://bethanybison.com"},
    {"school_name": "Chatham", "division": "D3", "conference": "PAC", "athletics_base_url": "https://chathamathletics.com"},
    {"school_name": "Geneva", "division": "D3", "conference": "PAC", "athletics_base_url": "https://genevaathletics.com"},
    {"school_name": "Grove City", "division": "D3", "conference": "PAC", "athletics_base_url": "https://gccathletics.com"},
    {"school_name": "Saint Vincent", "division": "D3", "conference": "PAC", "athletics_base_url": "https://svcathletics.com"},
    {"school_name": "Thiel", "division": "D3", "conference": "PAC", "athletics_base_url": "https://thielathletics.com"},
    {"school_name": "Thomas More", "division": "D3", "conference": "PAC", "athletics_base_url": "https://thomasmoresports.com"},
    {"school_name": "Washington & Jefferson", "division": "D3", "conference": "PAC", "athletics_base_url": "https://wjsports.com"},
    {"school_name": "Waynesburg", "division": "D3", "conference": "PAC", "athletics_base_url": "https://waynesburg.edu/athletics"},
    {"school_name": "Westminster (PA)", "division": "D3", "conference": "PAC", "athletics_base_url": "https://westminstertitans.com"},

    # SAA
    {"school_name": "Berry", "division": "D3", "conference": "SAA", "athletics_base_url": "https://berryathletics.com"},
    {"school_name": "Birmingham-Southern", "division": "D3", "conference": "SAA", "athletics_base_url": "https://bscsports.net"},
    {"school_name": "Centre", "division": "D3", "conference": "SAA", "athletics_base_url": "https://centrecolonels.com"},
    {"school_name": "Hendrix", "division": "D3", "conference": "SAA", "athletics_base_url": "https://hendrixwarriors.com"},
    {"school_name": "Millsaps", "division": "D3", "conference": "SAA", "athletics_base_url": "https://gomillsaps.com"},
    {"school_name": "Oglethorpe", "division": "D3", "conference": "SAA", "athletics_base_url": "https://oglethorpeathletics.com"},
    {"school_name": "Rhodes", "division": "D3", "conference": "SAA", "athletics_base_url": "https://rhodeslynx.com"},
    {"school_name": "Sewanee", "division": "D3", "conference": "SAA", "athletics_base_url": "https://sewaneetigers.com"},

    # SCAC
    {"school_name": "Austin College", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://acroos.com"},
    {"school_name": "Centenary (LA)", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://gocentenary.com"},
    {"school_name": "Colorado College", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://cctigers.com"},
    {"school_name": "Dallas", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://udallasathletics.com"},
    {"school_name": "Johnson University", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://johnsonu.edu/athletics"},
    {"school_name": "Ozarks", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://ozarkseagles.com"},
    {"school_name": "Schreiner", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://schreinerathletics.com"},
    {"school_name": "Southwestern (TX)", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://southwesternpirates.com"},
    {"school_name": "Texas Lutheran", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://tlubulldogs.com"},
    {"school_name": "Trinity (TX)", "division": "D3", "conference": "SCAC", "athletics_base_url": "https://trinitytigers.com"},

    # SCIAC
    {"school_name": "Cal Lutheran", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://clusports.com"},
    {"school_name": "Caltech", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://gocaltech.com"},
    {"school_name": "Chapman", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://chapmanathletics.com"},
    {"school_name": "Claremont-Mudd-Scripps", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://cmsathletics.com"},
    {"school_name": "La Verne", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://laverneathletics.com"},
    {"school_name": "Occidental", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://oxyathletics.com"},
    {"school_name": "Pomona-Pitzer", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://sagehens.com"},
    {"school_name": "Redlands", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://goredlands.com"},
    {"school_name": "Whittier", "division": "D3", "conference": "SCIAC", "athletics_base_url": "https://wcpoets.com"},

    # SLIAC
    {"school_name": "Blackburn", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://blackburnathletics.com"},
    {"school_name": "Eureka", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://eurekaathletics.com"},
    {"school_name": "Fontbonne", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://fontbonneathletics.com"},
    {"school_name": "Greenville", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://greenvilleathletics.com"},
    {"school_name": "Iowa Wesleyan", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://iwtigers.com"},
    {"school_name": "MacMurray", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://macathletics.com"},
    {"school_name": "Principia", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://principiaathletics.com"},
    {"school_name": "Spalding", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://spaldingathletics.com"},
    {"school_name": "Webster", "division": "D3", "conference": "SLIAC", "athletics_base_url": "https://websterathletics.com"},

    # SUNYAC
    {"school_name": "Brockport", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://brockportathletics.com"},
    {"school_name": "Buffalo State", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://buffalostateathletics.com"},
    {"school_name": "Cortland", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://cortlandreddragons.com"},
    {"school_name": "Fredonia", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://fredoniabluedevils.com"},
    {"school_name": "Geneseo", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://geneseoknights.com"},
    {"school_name": "New Paltz", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://newpaltzathletics.com"},
    {"school_name": "Oneonta", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://oneontaathletics.com"},
    {"school_name": "Oswego", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://oswegoathletics.com"},
    {"school_name": "Plattsburgh", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://plattsburghcardinals.com"},
    {"school_name": "Potsdam", "division": "D3", "conference": "SUNYAC", "athletics_base_url": "https://potsdambears.com"},

    # Skyline
    {"school_name": "Farmingdale State", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://farmingdaleathletics.com"},
    {"school_name": "Maritime (NY)", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://sunymaritime.edu/athletics"},
    {"school_name": "Mount Saint Mary (NY)", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://msmcknights.com"},
    {"school_name": "Mount Saint Vincent", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://msvdolphins.com"},
    {"school_name": "Old Westbury", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://oldwestburypanthers.com"},
    {"school_name": "Purchase", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://purchaseathletics.com"},
    {"school_name": "SUNY Maritime", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://sunymaritimeathletics.com"},
    {"school_name": "SUNY Old Westbury", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://oldwestburypanthers.com"},
    {"school_name": "St. Joseph's (Brooklyn)", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://sjcbearsathletics.com"},
    {"school_name": "St. Joseph's (LI)", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://sjcgoldeneagles.com"},
    {"school_name": "Yeshiva", "division": "D3", "conference": "Skyline", "athletics_base_url": "https://yumacs.com"},

    # UAA
    {"school_name": "Brandeis", "division": "D3", "conference": "UAA", "athletics_base_url": "https://brandeisjudges.com"},
    {"school_name": "Carnegie Mellon", "division": "D3", "conference": "UAA", "athletics_base_url": "https://athletics.cmu.edu"},
    {"school_name": "Case Western Reserve", "division": "D3", "conference": "UAA", "athletics_base_url": "https://cwruspartans.com"},
    {"school_name": "Chicago", "division": "D3", "conference": "UAA", "athletics_base_url": "https://athletics.uchicago.edu"},
    {"school_name": "Emory", "division": "D3", "conference": "UAA", "athletics_base_url": "https://emoryathletics.com"},
    {"school_name": "NYU", "division": "D3", "conference": "UAA", "athletics_base_url": "https://gonyuathletics.com"},
    {"school_name": "Rochester", "division": "D3", "conference": "UAA", "athletics_base_url": "https://uofrathletics.com"},
    {"school_name": "Wash U", "division": "D3", "conference": "UAA", "athletics_base_url": "https://wubears.com"},

    # UMAC
    {"school_name": "Crown", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://crownathletics.com"},
    {"school_name": "Finlandia", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://finlandiasports.com"},
    {"school_name": "Martin Luther", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://martinlutherknights.com"},
    {"school_name": "Northland", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://northlandathletics.com"},
    {"school_name": "Northwestern (MN)", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://nweagles.com"},
    {"school_name": "Presentation", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://presentationsaints.com"},
    {"school_name": "St. Scholastica", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://csssaints.com"},
    {"school_name": "Westminster (MO)", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://westminsterbluejays.com"},
    {"school_name": "Wisconsin Lutheran", "division": "D3", "conference": "UMAC", "athletics_base_url": "https://wlcwarriors.com"},

    # USA South
    {"school_name": "Agnes Scott", "division": "D3", "conference": "USA South", "athletics_base_url": "https://scotties.agnesscott.edu"},
    {"school_name": "Berea", "division": "D3", "conference": "USA South", "athletics_base_url": "https://bereamountaineers.com"},
    {"school_name": "Covenant", "division": "D3", "conference": "USA South", "athletics_base_url": "https://covenantscots.com"},
    {"school_name": "Greensboro", "division": "D3", "conference": "USA South", "athletics_base_url": "https://greensboropride.com"},
    {"school_name": "Huntingdon", "division": "D3", "conference": "USA South", "athletics_base_url": "https://huntingdonhawks.com"},
    {"school_name": "LaGrange", "division": "D3", "conference": "USA South", "athletics_base_url": "https://lagrangepanthers.com"},
    {"school_name": "Maryville (TN)", "division": "D3", "conference": "USA South", "athletics_base_url": "https://mcscotsathletics.com"},
    {"school_name": "Methodist", "division": "D3", "conference": "USA South", "athletics_base_url": "https://methodistathletics.com"},
    {"school_name": "N.C. Wesleyan", "division": "D3", "conference": "USA South", "athletics_base_url": "https://ncwu.edu/athletics"},
    {"school_name": "Pfeiffer", "division": "D3", "conference": "USA South", "athletics_base_url": "https://pfeifferfalcons.com"},
    {"school_name": "Piedmont", "division": "D3", "conference": "USA South", "athletics_base_url": "https://piedmontlions.com"},
    {"school_name": "William Peace", "division": "D3", "conference": "USA South", "athletics_base_url": "https://pacersports.com"},

    # WIAC
    {"school_name": "UW-Eau Claire", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwecblugolds.com"},
    {"school_name": "UW-La Crosse", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwlathletics.com"},
    {"school_name": "UW-Oshkosh", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwosports.com"},
    {"school_name": "UW-Platteville", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwppioneers.com"},
    {"school_name": "UW-River Falls", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwrfsports.com"},
    {"school_name": "UW-Stevens Point", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwsppointers.com"},
    {"school_name": "UW-Stout", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwstoutathletics.com"},
    {"school_name": "UW-Superior", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwsyellowjackets.com"},
    {"school_name": "UW-Whitewater", "division": "D3", "conference": "WIAC", "athletics_base_url": "https://uwwsports.com"},
]


def build_database(verify: bool = False):
    """Build the schools database CSV from known schools"""
    logger.info(f"Building schools database with {len(KNOWN_SCHOOLS)} known schools...")

    schools = []
    for entry in KNOWN_SCHOOLS:
        school = {
            'school_name': entry['school_name'],
            'division': entry['division'],
            'conference': entry.get('conference', ''),
            'athletics_base_url': entry['athletics_base_url'],
            'roster_url': entry.get('roster_url', '/sports/baseball/roster'),
            'stats_url': entry.get('stats_url', '/sports/baseball/stats'),
            'last_scraped': '',
            'scrape_priority': {'D1': 'high', 'D2': 'medium', 'D3': 'low'}.get(entry['division'], 'low'),
        }
        schools.append(school)

    # Sort: D1 first, then D2, then D3, then by name
    schools.sort(key=lambda x: ({'D1': 0, 'D2': 1, 'D3': 2}.get(x['division'], 3), x['school_name']))

    # Write CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(schools)

    d1 = len([s for s in schools if s['division'] == 'D1'])
    d2 = len([s for s in schools if s['division'] == 'D2'])
    d3 = len([s for s in schools if s['division'] == 'D3'])

    logger.info(f"Wrote {len(schools)} schools to {OUTPUT_FILE}")
    logger.info(f"  D1: {d1} schools")
    logger.info(f"  D2: {d2} schools")
    logger.info(f"  D3: {d3} schools")

    if verify:
        verify_urls(schools)


def verify_urls(schools: list):
    """Verify that roster URLs are reachable"""
    logger.info("Verifying roster URLs (this will take a while)...")

    session = requests.Session()
    session.headers['User-Agent'] = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )

    working = 0
    broken = 0

    for i, school in enumerate(schools):
        base = school['athletics_base_url'].rstrip('/')
        roster_url = f"{base}{school['roster_url']}"

        try:
            resp = session.get(roster_url, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                working += 1
                logger.debug(f"  OK: {school['school_name']} -> {roster_url}")
            else:
                broken += 1
                logger.warning(f"  FAIL ({resp.status_code}): {school['school_name']} -> {roster_url}")
        except Exception as e:
            broken += 1
            logger.warning(f"  ERROR: {school['school_name']} -> {roster_url}: {e}")

        if (i + 1) % 20 == 0:
            logger.info(f"  Verified {i + 1}/{len(schools)} ({working} OK, {broken} broken)")

        time.sleep(random.uniform(2, 4))

    logger.info(f"Verification complete: {working} working, {broken} broken out of {len(schools)}")


def show_stats():
    """Show stats about the current database"""
    if not OUTPUT_FILE.exists():
        print("No schools database found. Run 'python build_schools_db.py' first.")
        return

    schools = []
    with open(OUTPUT_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        schools = list(reader)

    d1 = [s for s in schools if s['division'] == 'D1']
    d2 = [s for s in schools if s['division'] == 'D2']
    d3 = [s for s in schools if s['division'] == 'D3']

    conferences = {}
    for s in schools:
        conf = s.get('conference', 'Unknown')
        conferences.setdefault(conf, []).append(s)

    print(f"\nSchools Database: {OUTPUT_FILE}")
    print(f"Total: {len(schools)} schools")
    print(f"  D1: {len(d1)}")
    print(f"  D2: {len(d2)}")
    print(f"  D3: {len(d3)}")
    print(f"\nConferences: {len(conferences)}")
    for conf in sorted(conferences.keys()):
        members = conferences[conf]
        divs = set(m['division'] for m in members)
        print(f"  {conf}: {len(members)} schools ({', '.join(sorted(divs))})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build schools database')
    parser.add_argument('--verify', action='store_true', help='Verify all URLs are reachable')
    parser.add_argument('--stats', action='store_true', help='Show database stats')
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        build_database(verify=args.verify)
