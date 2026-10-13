# -*- coding: utf-8 -*-
"""
crop_recommender.py
===================
Agricultural Crop Recommendation Engine for Karnataka & Regional Agro-Climatic Zones.

Evaluates crop suitability using verified, evidence-based agricultural rules and
district cropping patterns from:
- University of Agricultural Sciences (UAS) Bangalore, Dharwad, Raichur, Shivamogga
- ICAR Package of Practices
- Karnataka State Department of Agriculture (KSDA) District Cropping Statistics

Features:
- Highly location-specific recommendations reflecting real crops local farmers grow.
- Dynamic scoring based on district prevalence, soil texture, water source, and season.
- Support for Groq AI engine for out-of-state or custom regional queries.
"""

from __future__ import annotations

import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# Representative coordinate centers for all 31 Karnataka districts
KARNATAKA_DISTRICT_COORDS: Dict[str, Tuple[float, float]] = {
    "Bagalkote": (16.1691, 75.6615),
    "Ballari": (15.1394, 76.9214),
    "Belagavi": (15.8497, 74.4977),
    "Bengaluru Rural": (13.2257, 77.5750),
    "Bengaluru Urban": (12.9716, 77.5946),
    "Bidar": (17.9104, 77.5199),
    "Chamarajanagara": (11.9261, 76.9437),
    "Chikkaballapura": (13.4325, 77.7275),
    "Chikkamagaluru": (13.3161, 75.7720),
    "Chitradurga": (14.2251, 76.3980),
    "Dakshina Kannada": (12.8703, 74.8806),
    "Davanagere": (14.4644, 75.9218),
    "Dharwad": (15.4589, 75.0078),
    "Gadag": (15.4316, 75.6355),
    "Hassan": (13.0072, 76.1029),
    "Haveri": (14.7954, 75.3991),
    "Kalaburagi": (17.3297, 76.8343),
    "Kodagu": (12.4244, 75.7382),
    "Kolar": (13.1367, 78.1291),
    "Koppal": (15.3468, 76.1557),
    "Mandya": (12.5229, 76.8978),
    "Mysuru": (12.2958, 76.6394),
    "Raichur": (16.2120, 77.3439),
    "Ramanagara": (12.7209, 77.2799),
    "Shivamogga": (13.9299, 75.5681),
    "Tumakuru": (13.3392, 77.1017),
    "Udupi": (13.3409, 74.7421),
    "Uttara Kannada": (14.7937, 74.5540),
    "Vijayapura": (16.8302, 75.7100),
    "Vijayanagara": (15.2689, 76.3909),
    "Yadgir": (16.7628, 77.1442)
}

# Verified District-to-Major-Crops cropping profile based on KSDA & UAS surveys
DISTRICT_CROP_PROFILES: Dict[str, List[str]] = {
    "Kalaburagi": ["Red Gram (Tur)", "Bengal Gram", "Jowar", "Soybean", "Sunflower", "Cotton"],
    "Bidar": ["Red Gram (Tur)", "Soybean", "Bengal Gram", "Jowar", "Sugarcane"],
    "Yadgir": ["Red Gram (Tur)", "Cotton", "Paddy", "Groundnut", "Jowar"],
    "Vijayapura": ["Jowar", "Bengal Gram", "Pomegranate", "Sunflower", "Wheat", "Maize"],
    "Bagalkote": ["Sugarcane", "Bengal Gram", "Maize", "Sunflower", "Pomegranate", "Jowar"],
    "Dharwad": ["Cotton", "Soybean", "Maize", "Chilli", "Bengal Gram", "Wheat", "Jowar"],
    "Belagavi": ["Sugarcane", "Soybean", "Maize", "Cotton", "Bengal Gram", "Wheat"],
    "Haveri": ["Maize", "Chilli", "Cotton", "Soybean", "Groundnut", "Jowar"],
    "Gadag": ["Bengal Gram", "Onion", "Groundnut", "Cotton", "Jowar", "Sunflower"],
    "Raichur": ["Paddy", "Cotton", "Chilli", "Groundnut", "Jowar", "Sunflower"],
    "Ballari": ["Cotton", "Chilli", "Paddy", "Maize", "Pomegranate", "Sunflower"],
    "Vijayanagara": ["Cotton", "Paddy", "Maize", "Chilli", "Sunflower"],
    "Koppal": ["Paddy", "Maize", "Pomegranate", "Sunflower", "Groundnut"],
    "Mandya": ["Sugarcane", "Paddy", "Ragi", "Banana"],
    "Mysuru": ["Paddy", "Ragi", "Sugarcane", "Cotton", "Banana"],
    "Hassan": ["Potato", "Coffee", "Maize", "Ragi", "Paddy"],
    "Chitradurga": ["Groundnut", "Onion", "Ragi", "Maize", "Pomegranate"],
    "Tumakuru": ["Groundnut", "Ragi", "Arecanut", "Maize", "Pomegranate"],
    "Kolar": ["Tomato", "Ragi", "Groundnut", "Maize"],
    "Chikkaballapura": ["Tomato", "Ragi", "Maize", "Groundnut"],
    "Bengaluru Rural": ["Ragi", "Tomato", "Maize", "Groundnut"],
    "Bengaluru Urban": ["Ragi", "Tomato", "Maize"],
    "Ramanagara": ["Ragi", "Banana", "Tomato", "Groundnut"],
    "Chamarajanagara": ["Sugarcane", "Banana", "Maize", "Ragi", "Groundnut"],
    "Davanagere": ["Maize", "Paddy", "Arecanut", "Cotton", "Sugarcane"],
    "Shivamogga": ["Arecanut", "Paddy", "Ginger", "Maize", "Sugarcane"],
    "Chikkamagaluru": ["Coffee", "Arecanut", "Paddy", "Maize"],
    "Kodagu": ["Coffee", "Paddy", "Arecanut"],
    "Dakshina Kannada": ["Arecanut", "Paddy", "Banana"],
    "Udupi": ["Paddy", "Arecanut", "Banana"],
    "Uttara Kannada": ["Arecanut", "Paddy", "Sugarcane"],
}

# Verified Agronomic Rules for Crops
VERIFIED_CROP_RULES: Dict[str, Dict[str, Any]] = {
    "Ragi": {
        "botanical_name": "Eleusine coracana (Finger Millet)",
        "kannada_name": "ರಾಗಿ (Ragi)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)", "Summer"],
        "duration_days": "105 - 120 days",
        "suitable_soils": ["Sandy loam", "Loam", "Sandy clay loam", "Silt loam", "Sand"],
        "unsuitable_soils": ["Clay", "Silty clay", "Black clay"],
        "water_need_mm": "350 - 450 mm",
        "water_category": "Low (Drought-hardy)",
        "optimal_temp_range_c": (18.0, 34.0),
        "primary_districts": [
            "Tumakuru", "Mandya", "Hassan", "Mysuru", "Bengaluru Rural",
            "Ramanagara", "Kolar", "Chikkaballapura", "Chitradurga", "Chamarajanagara"
        ],
        "strengths": [
            "Exceptional drought resilience and low input cost.",
            "Thrives in light to red sandy loam soils with minimal irrigation.",
            "High nutritional value and guaranteed local market demand."
        ],
        "risks": [
            "Susceptible to blast disease during prolonged humid/cloudy spells.",
            "Poor germination if sown during excessive soil waterlogging."
        ],
        "source": "UAS Bangalore Package of Practices & ICAR-AICRP on Small Millets"
    },
    "Maize": {
        "botanical_name": "Zea mays (Corn)",
        "kannada_name": "ಮೆಕ್ಕೆಜೋಳ (Mekke Jola)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)", "Rabi", "Rabi (Winter)"],
        "duration_days": "90 - 110 days",
        "suitable_soils": ["Sandy clay loam", "Clay loam", "Loam", "Silt loam"],
        "unsuitable_soils": ["Sand", "Loamy sand"],
        "water_need_mm": "500 - 650 mm",
        "water_category": "Moderate",
        "optimal_temp_range_c": (18.0, 35.0),
        "primary_districts": [
            "Davanagere", "Haveri", "Belagavi", "Ballari", "Shivamogga",
            "Dharwad", "Chitradurga", "Chikkamagaluru", "Bagalkote"
        ],
        "strengths": [
            "High biomass and yield potential under responsive fertilizer management.",
            "Well-established poultry feed and industrial starch mandi network.",
            "Fits well in crop rotations following legumes."
        ],
        "risks": [
            "Extremely sensitive to waterlogging; demands well-drained field conditions.",
            "Vulnerable to Fall Armyworm (FAW) requiring timely pheromone trap scouting."
        ],
        "source": "UAS Dharwad Package of Practices & ICAR-IIMR"
    },
    "Groundnut": {
        "botanical_name": "Arachis hypogaea (Peanut)",
        "kannada_name": "ಕಡಲೆಕಾಯಿ (Kadlekayi)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)", "Summer", "Rabi"],
        "duration_days": "105 - 125 days",
        "suitable_soils": ["Sandy loam", "Loam", "Sandy clay loam", "Loamy sand"],
        "unsuitable_soils": ["Clay", "Silty clay", "Heavy black clay"],
        "water_need_mm": "450 - 550 mm",
        "water_category": "Moderate",
        "optimal_temp_range_c": (20.0, 32.0),
        "primary_districts": [
            "Chitradurga", "Tumakuru", "Ballari", "Vijayapura", "Gadag",
            "Kolar", "Bagalkote", "Koppal", "Haveri"
        ],
        "strengths": [
            "Atmospheric nitrogen-fixing legume, enriching soil health.",
            "High economic value of oilseed and valuable nutritious fodder haulms.",
            "Moderate water requirement with good drought tolerance."
        ],
        "risks": [
            "Heavy sticky clay soils prevent gynophore (peg) penetration into the ground.",
            "Critical moisture stress at flowering or pegging drastically reduces pod yield."
        ],
        "source": "UAS Raichur & ICAR-Directorate of Groundnut Research (DGR)"
    },
    "Paddy": {
        "botanical_name": "Oryza sativa (Paddy / Rice)",
        "kannada_name": "ಭತ್ತ (Bhatta)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)", "Summer"],
        "duration_days": "120 - 135 days",
        "suitable_soils": ["Clay", "Silty clay", "Clay loam", "Silty clay loam"],
        "unsuitable_soils": ["Sand", "Loamy sand", "Coarse gravelly soils"],
        "water_need_mm": "1100 - 1400 mm",
        "water_category": "High (Requires assured irrigation or flooded conditions)",
        "optimal_temp_range_c": (22.0, 36.0),
        "primary_districts": [
            "Mandya", "Shivamogga", "Raichur", "Davanagere", "Udupi",
            "Dakshina Kannada", "Uttara Kannada", "Mysuru", "Koppal", "Ballari"
        ],
        "strengths": [
            "Ideal for heavy soils with high water-retention capacity.",
            "Assured MSP procurement and staple food demand across markets."
        ],
        "risks": [
            "Requires substantial, reliable irrigation; prone to failure under water deficits.",
            "Higher labour requirement for nursery raising, transplanting, and weeding."
        ],
        "source": "VC Farm Mandya (UAS Bangalore) & ICAR-NRRI"
    },
    "Rice": {  # Alias for Paddy
        "botanical_name": "Oryza sativa (Paddy / Rice)",
        "kannada_name": "ಭತ್ತ (Bhatta)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)", "Summer"],
        "duration_days": "120 - 135 days",
        "suitable_soils": ["Clay", "Silty clay", "Clay loam", "Silty clay loam"],
        "unsuitable_soils": ["Sand", "Loamy sand", "Coarse gravelly soils"],
        "water_need_mm": "1100 - 1400 mm",
        "water_category": "High (Requires assured irrigation or flooded conditions)",
        "optimal_temp_range_c": (22.0, 36.0),
        "primary_districts": [
            "Mandya", "Shivamogga", "Raichur", "Davanagere", "Udupi",
            "Dakshina Kannada", "Uttara Kannada", "Mysuru", "Koppal"
        ],
        "strengths": [
            "Ideal for heavy soils with high water-retention capacity.",
            "Assured MSP procurement and staple food demand across markets."
        ],
        "risks": [
            "Requires substantial, reliable irrigation; prone to failure under water deficits.",
            "Higher labour requirement for nursery raising, transplanting, and weeding."
        ],
        "source": "VC Farm Mandya (UAS Bangalore) & ICAR-NRRI"
    },
    "Wheat": {
        "botanical_name": "Triticum aestivum (Wheat)",
        "kannada_name": "ಗೋಧಿ (Godhi)",
        "preferred_seasons": ["Rabi", "Rabi (Winter)"],
        "duration_days": "105 - 125 days",
        "suitable_soils": ["Clay loam", "Loam", "Clay", "Sandy clay loam"],
        "unsuitable_soils": ["Sand", "Loamy sand"],
        "water_need_mm": "350 - 450 mm",
        "water_category": "Moderate (Requires 3-4 timely irrigations)",
        "optimal_temp_range_c": (12.0, 26.0),
        "primary_districts": [
            "Vijayapura", "Bagalkote", "Dharwad", "Belagavi", "Gadag", "Bidar"
        ],
        "strengths": [
            "Excellent Rabi crop for northern Karnataka black cotton soils.",
            "Lower pest pressure during cold winter months compared to Kharif crops."
        ],
        "risks": [
            "High temperatures during grain-filling stage cause terminal heat stress.",
            "Unsuitable for Southern or Coastal Karnataka due to warm winter temperatures."
        ],
        "source": "UAS Dharwad & ICAR-IIWBR"
    },
    "Red Gram (Tur)": {
        "botanical_name": "Cajanus cajan (Pigeon Pea / Tur Dal)",
        "kannada_name": "ತೊಗರಿ (Togari)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)"],
        "duration_days": "150 - 180 days",
        "suitable_soils": ["Clay loam", "Clay", "Sandy clay loam", "Loam"],
        "unsuitable_soils": ["Sand", "Waterlogged soils"],
        "water_need_mm": "400 - 550 mm",
        "water_category": "Low (Deep-rooted drought-hardy pulse)",
        "optimal_temp_range_c": (20.0, 38.0),
        "primary_districts": ["Kalaburagi", "Bidar", "Yadgir", "Raichur", "Vijayapura"],
        "strengths": [
            "Kalaburagi is the GI-tagged Red Gram bowl of India with assured market demand.",
            "Enriches soil fertility through massive atmospheric nitrogen fixation.",
            "Extremely resilient to dry spells with deep tap root system."
        ],
        "risks": [
            "Susceptible to pod borer (Helicoverpa armigera) requiring IPM.",
            "Sensitive to standing water or prolonged field waterlogging."
        ],
        "source": "UAS Raichur & ICAR-IIPR"
    },
    "Bengal Gram": {
        "botanical_name": "Cicer arietinum (Chickpea / Chana)",
        "kannada_name": "ಕಡಲೆ (Kadale)",
        "preferred_seasons": ["Rabi", "Rabi (Winter)"],
        "duration_days": "90 - 105 days",
        "suitable_soils": ["Clay loam", "Clay", "Sandy clay loam", "Silty clay"],
        "unsuitable_soils": ["Sand", "Saline soils"],
        "water_need_mm": "250 - 350 mm",
        "water_category": "Low (Residual moisture winter pulse)",
        "optimal_temp_range_c": (15.0, 29.0),
        "primary_districts": ["Vijayapura", "Bagalkote", "Gadag", "Kalaburagi", "Dharwad", "Bidar", "Belagavi"],
        "strengths": [
            "Thrives on conserved residual soil moisture in northern black cotton soils.",
            "Low input cost and quick 90-day turnaround.",
            "High market price and guaranteed MSP procurement."
        ],
        "risks": [
            "Susceptible to Fusarium wilt in non-resistant cultivars.",
            "Excess moisture at flowering causes flower drop."
        ],
        "source": "UAS Dharwad & ICAR-IIPR"
    },
    "Cotton": {
        "botanical_name": "Gossypium hirsutum (Cotton)",
        "kannada_name": "ಹತ್ತಿ (Hatti)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)"],
        "duration_days": "150 - 170 days",
        "suitable_soils": ["Clay", "Clay loam", "Sandy clay loam", "Silty clay"],
        "unsuitable_soils": ["Sand", "Shallow gravelly soils"],
        "water_need_mm": "600 - 750 mm",
        "water_category": "Moderate to High",
        "optimal_temp_range_c": (21.0, 36.0),
        "primary_districts": ["Dharwad", "Belagavi", "Haveri", "Ballari", "Raichur", "Yadgir", "Kalaburagi", "Vijayanagara"],
        "strengths": [
            "Premier commercial cash crop with large regional ginning ecosystem.",
            "High gross returns in deep northern black soils.",
            "Good drought resistance during vegetative growth stage."
        ],
        "risks": [
            "Vulnerable to sucking pests (thrips, aphids) and pink bollworm.",
            "Demands timely picking before unseasonal rains."
        ],
        "source": "UAS Dharwad & ICAR-CICR"
    },
    "Sugarcane": {
        "botanical_name": "Saccharum officinarum (Sugarcane)",
        "kannada_name": "ಕಬ್ಬು (Kabbu)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer", "Kharif (Monsoon)"],
        "duration_days": "330 - 365 days (Annual)",
        "suitable_soils": ["Clay loam", "Clay", "Loam", "Silty clay loam"],
        "unsuitable_soils": ["Sand", "Shallow rocky soils"],
        "water_need_mm": "1500 - 2200 mm",
        "water_category": "High (Heavy irrigation mandatory)",
        "optimal_temp_range_c": (20.0, 38.0),
        "primary_districts": ["Mandya", "Belagavi", "Bagalkote", "Mysuru", "Shivamogga", "Chamarajanagara", "Davanagere"],
        "strengths": [
            "Assured factory gate procurement by sugar mills under statutory FRP pricing.",
            "Robust biomass and multiple ratoon crop cycles.",
            "High financial returns for farmers with assured canal/borewell water."
        ],
        "risks": [
            "Completely unsuitable without assured irrigation.",
            "Long crop duration locks land for 12 months."
        ],
        "source": "VC Farm Mandya (UAS Bangalore) & ICAR-SBI"
    },
    "Jowar": {
        "botanical_name": "Sorghum bicolor (Sorghum / Maldandi)",
        "kannada_name": "ಜೋಳ (Jola / Bili Jola)",
        "preferred_seasons": ["Kharif", "Rabi", "Rabi (Winter)"],
        "duration_days": "110 - 125 days",
        "suitable_soils": ["Clay", "Clay loam", "Sandy clay loam", "Loam"],
        "unsuitable_soils": ["Sand", "Acidic shallow soils"],
        "water_need_mm": "350 - 450 mm",
        "water_category": "Low (Supreme drought tolerance)",
        "optimal_temp_range_c": (18.0, 36.0),
        "primary_districts": ["Vijayapura", "Kalaburagi", "Bagalkote", "Dharwad", "Raichur", "Gadag", "Haveri", "Yadgir"],
        "strengths": [
            "Staple food grain (Jolada Rotti) with huge price premium for Maldandi M35-1.",
            "Valuable nutritious dry fodder for livestock.",
            "Extremely hardy and thrives under high moisture stress."
        ],
        "risks": [
            "Susceptible to shoot fly in late sowings.",
            "Grain mold if rains coincide with harvest."
        ],
        "source": "UAS Dharwad & ICAR-IIMR"
    },
    "Soybean": {
        "botanical_name": "Glycine max (Soybean)",
        "kannada_name": "ಸೋಯಾಬೀನ್ (Soyabean)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)"],
        "duration_days": "90 - 105 days",
        "suitable_soils": ["Clay loam", "Clay", "Sandy clay loam", "Loam"],
        "unsuitable_soils": ["Sand", "Waterlogged soils"],
        "water_need_mm": "450 - 550 mm",
        "water_category": "Moderate",
        "optimal_temp_range_c": (20.0, 34.0),
        "primary_districts": ["Belagavi", "Dharwad", "Bidar", "Haveri", "Kalaburagi"],
        "strengths": [
            "Short-duration cash pulse/oilseed fitting perfectly in double-cropping.",
            "High oil and protein content with active oil extraction factories.",
            "Improves soil health for succeeding Rabi wheat or chickpea."
        ],
        "risks": [
            "Pod shattering if harvest is delayed after maturity.",
            "Susceptible to yellow mosaic virus."
        ],
        "source": "UAS Dharwad & ICAR-IISR"
    },
    "Chilli": {
        "botanical_name": "Capsicum annuum (Byadgi Chilli)",
        "kannada_name": "ಮೆಣಸಿನಕಾಯಿ (Menasinakayi / Byadgi)",
        "preferred_seasons": ["Kharif", "Kharif (Monsoon)"],
        "duration_days": "150 - 180 days",
        "suitable_soils": ["Clay loam", "Sandy loam", "Loam", "Sandy clay loam"],
        "unsuitable_soils": ["Heavy waterlogged clay", "Gravelly sand"],
        "water_need_mm": "600 - 750 mm",
        "water_category": "Moderate (Requires well-drained conditions)",
        "optimal_temp_range_c": (18.0, 32.0),
        "primary_districts": ["Haveri", "Dharwad", "Ballari", "Gadag", "Raichur", "Vijayanagara"],
        "strengths": [
            "GI-tagged Byadgi chilli with huge international export and oleoresin demand.",
            "High market value per quintal at Byadgi APMC.",
            "Suitable for intercropping with onion or coriander."
        ],
        "risks": [
            "Susceptible to thrips and leaf curl virus (Gemini virus).",
            "Sensitive to sudden waterlogging and root rot."
        ],
        "source": "UAS Dharwad Horticultural Wing & ICAR-IIHR"
    },
    "Tomato": {
        "botanical_name": "Solanum lycopersicum (Tomato)",
        "kannada_name": "ಟೊಮೇಟೊ (Tomato)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer"],
        "duration_days": "110 - 130 days",
        "suitable_soils": ["Sandy loam", "Loam", "Sandy clay loam"],
        "unsuitable_soils": ["Heavy poorly-drained clay"],
        "water_need_mm": "500 - 650 mm",
        "water_category": "Moderate",
        "optimal_temp_range_c": (18.0, 32.0),
        "primary_districts": ["Kolar", "Chikkaballapura", "Belagavi", "Bengaluru Rural", "Hassan", "Ramanagara"],
        "strengths": [
            "Kolar is home to Asia's second largest tomato APMC market.",
            "High-yield horticultural crop with multi-harvest cash inflow.",
            "Well-established cold storage and transport infrastructure."
        ],
        "risks": [
            "High price volatility in seasonal wholesale markets.",
            "Requires strict staking and preventive spraying for late blight."
        ],
        "source": "UAS Bangalore & ICAR-IIHR Hessaraghatta"
    },
    "Arecanut": {
        "botanical_name": "Areca catechu (Betel Nut / Arecanut)",
        "kannada_name": "ಅಡಿಕೆ (Adike)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer", "Kharif (Monsoon)"],
        "duration_days": "Perennial Plantation",
        "suitable_soils": ["Clay loam", "Sandy clay loam", "Laterite soil", "Loam"],
        "unsuitable_soils": ["Shallow rocky soils", "Waterlogged soils"],
        "water_need_mm": "1200 - 1800 mm",
        "water_category": "High (Requires regular irrigation in dry months)",
        "optimal_temp_range_c": (16.0, 35.0),
        "primary_districts": ["Shivamogga", "Chikkamagaluru", "Dakshina Kannada", "Uttara Kannada", "Udupi", "Davanagere", "Tumakuru"],
        "strengths": [
            "Highest revenue-generating plantation crop in Malnad & Coastal belts.",
            "Guaranteed long-term economic security with CAMPCO cooperative.",
            "Allows multi-tier intercropping with black pepper, cocoa, and banana."
        ],
        "risks": [
            "High initial capital investment and gestation period (4-5 years).",
            "Vulnerable to Koleroga (fruit rot) during heavy South-West monsoon."
        ],
        "source": "UAS Shivamogga & ICAR-CPCRI"
    },
    "Onion": {
        "botanical_name": "Allium cepa (Onion)",
        "kannada_name": "ಈರುಳ್ಳಿ (Eerulli)",
        "preferred_seasons": ["Kharif", "Rabi"],
        "duration_days": "90 - 110 days",
        "suitable_soils": ["Sandy loam", "Loam", "Clay loam", "Sandy clay loam"],
        "unsuitable_soils": ["Heavy compact clay", "Stony soils"],
        "water_need_mm": "400 - 550 mm",
        "water_category": "Moderate",
        "optimal_temp_range_c": (15.0, 32.0),
        "primary_districts": ["Chitradurga", "Gadag", "Dharwad", "Bagalkote", "Vijayapura", "Haveri"],
        "strengths": [
            "Quick cash turnover with major APMC auctions in Chitradurga and Hubballi.",
            "Fits easily into crop rotations with pulses and millets.",
            "Good export demand for Bellary/Bangalore Rose varieties."
        ],
        "risks": [
            "Storage rotting if harvested in unseasonal wet weather.",
            "Market price fluctuations."
        ],
        "source": "ICAR-DOGR"
    },
    "Sunflower": {
        "botanical_name": "Helianthus annuus (Sunflower)",
        "kannada_name": "ಸೂರ್ಯಕಾಂತಿ (Suryakanti)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer"],
        "duration_days": "85 - 95 days",
        "suitable_soils": ["Clay loam", "Clay", "Sandy clay loam", "Loam"],
        "unsuitable_soils": ["Sand", "Acidic soils"],
        "water_need_mm": "350 - 450 mm",
        "water_category": "Low to Moderate",
        "optimal_temp_range_c": (18.0, 35.0),
        "primary_districts": ["Koppal", "Raichur", "Ballari", "Bagalkote", "Gadag", "Kalaburagi", "Vijayanagara"],
        "strengths": [
            "High-demand domestic edible oilseed crop.",
            "Short duration fits all three cropping seasons.",
            "Extensive taproot extracts subsoil moisture effectively."
        ],
        "risks": [
            "Parrot and bird damage during seed hardening stage.",
            "Necrosis disease spread by thrips."
        ],
        "source": "ICAR-IIOR"
    },
    "Banana": {
        "botanical_name": "Musa acuminata (Banana)",
        "kannada_name": "ಬಾಳೆ (Bale)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer"],
        "duration_days": "300 - 365 days",
        "suitable_soils": ["Clay loam", "Loam", "Sandy clay loam", "Silty clay"],
        "unsuitable_soils": ["Sand", "Saline soils"],
        "water_need_mm": "1400 - 1800 mm",
        "water_category": "High (Demands drip/furrow irrigation)",
        "optimal_temp_range_c": (20.0, 38.0),
        "primary_districts": ["Mandya", "Mysuru", "Ramanagara", "Chamarajanagara", "Shivamogga", "Belagavi", "Udupi", "Dakshina Kannada"],
        "strengths": [
            "Fast return perennial commercial fruit crop with weekly harvests.",
            "Huge local demand for Yelakki (GI tagged Nanjangud/Mysuru) and Grand Naine.",
            "Leaves and flowers provide supplementary farm income."
        ],
        "risks": [
            "Severe wind lodging during monsoon storms without propping.",
            "Susceptible to Panama wilt and Sigatoka leaf spot."
        ],
        "source": "ICAR-NRCB & UAS Bangalore"
    },
    "Pomegranate": {
        "botanical_name": "Punica granatum (Pomegranate / Bhagwa)",
        "kannada_name": "ದಾಳಿಂಬೆ (Dalimbe)",
        "preferred_seasons": ["Kharif", "Rabi", "Summer"],
        "duration_days": "Perennial Horticulture (Bhagwa)",
        "suitable_soils": ["Clay loam", "Sandy loam", "Loam", "Sandy clay loam"],
        "unsuitable_soils": ["Waterlogged heavy black clay without drainage"],
        "water_need_mm": "600 - 800 mm",
        "water_category": "Low to Moderate (Drought-hardy fruit crop)",
        "optimal_temp_range_c": (20.0, 38.0),
        "primary_districts": ["Vijayapura", "Bagalkote", "Chitradurga", "Koppal", "Ballari", "Tumakuru"],
        "strengths": [
            "Extremely high export and domestic value for Bhagwa ruby arils.",
            "Thrives in dry, semi-arid Deccan plateau climate.",
            "High water use efficiency under drip irrigation."
        ],
        "risks": [
            "Bacterial blight (Telya) requires vigilant copper sanitation.",
            "High initial orchard establishment cost."
        ],
        "source": "ICAR-NRCP & UAS Raichur"
    },
    "Coffee": {
        "botanical_name": "Coffea arabica / canephora (Coffee)",
        "kannada_name": "ಕಾಫಿ (Coffee)",
        "preferred_seasons": ["Kharif", "Rabi"],
        "duration_days": "Perennial Shade Plantation",
        "suitable_soils": ["Clay loam", "Sandy clay loam", "Laterite soil", "Loam"],
        "unsuitable_soils": ["Heavy sticky clay", "Alkaline soils"],
        "water_need_mm": "1500 - 2500 mm",
        "water_category": "High (Thrives in Western Ghats rainfall belt)",
        "optimal_temp_range_c": (15.0, 30.0),
        "primary_districts": ["Chikkamagaluru", "Kodagu", "Hassan"],
        "strengths": [
            "Premier global export commodity with Coffee Board auctions.",
            "Intercropped with high-value black pepper and cardamom.",
            "Shade-grown biodiversity model preserves plantation ecology."
        ],
        "risks": [
            "White stem borer in Arabica requires strict monitoring.",
            "Sensitive to erratic blossom rains in March-April."
        ],
        "source": "CCRI Balehonnur & Coffee Board"
    }
}


def resolve_district_name(district_input: str, lat: float = 0.0, lon: float = 0.0) -> str:
    """
    Match user input or geocoded district string to canonical Karnataka district name.
    If ambiguous or 'Local District', resolves to nearest district by coordinates.
    """
    clean = str(district_input or "").strip()

    # Direct match in profiles
    for canon in DISTRICT_CROP_PROFILES.keys():
        if canon.lower() == clean.lower() or canon.lower() in clean.lower():
            return canon

    # Coordinate distance match
    if lat and lon:
        closest = "Dharwad"
        min_d = float("inf")
        for dist, (dlat, dlon) in KARNATAKA_DISTRICT_COORDS.items():
            dist_sq = (dlat - lat) ** 2 + (dlon - lon) ** 2
            if dist_sq < min_d:
                min_d = dist_sq
                closest = dist
        return closest

    return clean or "Dharwad"


def evaluate_crop_suitability(
    crop_name: str,
    soil_type: str,
    district: str,
    current_season: str,
    avg_max_temp: float,
    has_irrigation: bool = True
) -> Dict[str, Any]:
    """
    Evaluate single crop suitability against agronomic rules and district prevalence.
    Returns numeric score (0-100), suitability status, reasons, and risks.
    """
    rule = VERIFIED_CROP_RULES.get(crop_name)
    if not rule:
        # Fallback dummy rule if unknown
        rule = VERIFIED_CROP_RULES["Ragi"]

    score = 0
    reasons: List[str] = []
    risks = list(rule.get("risks", []))

    canon_district = resolve_district_name(district)
    district_crops = DISTRICT_CROP_PROFILES.get(canon_district, [])

    # 1. District Cropping Prevalence (Max 45 points)
    # Reflects the ground reality of what farmers actually cultivate in this district
    if crop_name in district_crops:
        idx = district_crops.index(crop_name)
        bonus = max(45 - (idx * 5), 25)
        score += bonus
        reasons.append(
            f"Major local crop: {crop_name} is ranked #{idx + 1} most cultivated crop in {canon_district} with proven farmer adoption and local mandi auctions."
        )
    elif any(canon_district.lower() in d.lower() for d in rule.get("primary_districts", [])):
        score += 25
        reasons.append(
            f"Agro-climatic suitability: {canon_district} belongs to the recommended agro-climatic zone for {crop_name}."
        )
    else:
        score += 5
        risks.append(
            f"Uncommon local crop: {crop_name} is not widely grown in {canon_district}; ensure local market and input availability before planting."
        )

    # 2. Soil Texture Compatibility (Max 25 points)
    soil_norm = (soil_type or "Loam").strip()
    suitable_soils = [s.lower() for s in rule.get("suitable_soils", [])]
    unsuitable_soils = [u.lower() for u in rule.get("unsuitable_soils", [])]

    if any(soil_norm.lower() in s for s in suitable_soils):
        score += 25
        reasons.append(f"Optimal soil condition: {soil_norm} supports root aeration and nutrient uptake for {crop_name}.")
    elif any(soil_norm.lower() in u for u in unsuitable_soils):
        score += 5
        risks.append(f"Suboptimal soil texture: {soil_norm} may cause drainage or pegging constraints for {crop_name}.")
    else:
        score += 15
        reasons.append(f"Acceptable soil texture: {soil_norm} provides moderate suitability under appropriate tillage and farmyard manure.")

    # 3. Water & Irrigation Alignment (Max 15 points)
    water_cat = rule.get("water_category", "Moderate")
    if has_irrigation:
        score += 15
        reasons.append("Irrigation security: Assured water supply supports full vegetative and reproductive phases.")
    else:
        # Rainfed land
        if "Low" in water_cat or "Drought" in water_cat:
            score += 15
            reasons.append(f"Drought tolerance: {crop_name} is resilient under dryland rainfed conditions.")
        elif "High" in water_cat:
            score = max(score - 30, 5)
            risks.append(f"High water risk: {crop_name} demands assured irrigation ({rule.get('water_need_mm', 'high')}); rainfed farming has high failure risk.")
        else:
            score += 8
            risks.append(f"Moisture dependency: Dry spells during critical growth stages may reduce yield.")

    # 4. Seasonal Window (Max 10 points)
    season_norm = current_season.split()[0] if current_season else "Kharif"
    preferred_seasons = [s.lower() for s in rule.get("preferred_seasons", [])]
    if any(season_norm.lower() in p for p in preferred_seasons):
        score += 10
        reasons.append(f"Seasonal match: {current_season} coincides with standard sowing window.")
    else:
        score += 2
        risks.append(f"Off-season sowing: Current period ({current_season}) is outside standard sowing window.")

    # 5. Temperature Window (Max 5 points)
    min_temp, max_temp = rule.get("optimal_temp_range_c", (18.0, 35.0))
    if min_temp <= avg_max_temp <= max_temp:
        score += 5
    else:
        score += 1

    # Final Classification
    if score >= 75:
        suitability = "Highly Suitable"
    elif score >= 55:
        suitability = "Potentially Suitable"
    else:
        suitability = "Uncertain / Higher Risk"

    return {
        "crop": crop_name,
        "botanical_name": rule.get("botanical_name", crop_name),
        "kannada_name": rule.get("kannada_name", crop_name),
        "suitability": suitability,
        "suitability_score": min(score, 100),
        "duration_days": rule.get("duration_days", "90 - 120 days"),
        "water_needs": f"{rule.get('water_need_mm', '450 mm')} ({rule.get('water_category', 'Moderate')})",
        "reasons": reasons,
        "risks": risks,
        "missing_information": [
            "Physical soil laboratory test (soil pH, available N-P-K, organic carbon %)",
            "Actual on-farm borewell discharge or canal scheduling details"
        ],
        "source": rule.get("source", "ICAR & UAS Package of Practices")
    }


def recommend_crops(
    location_data: Dict[str, Any],
    farmer_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dynamically recommend the most probable crops for a farmer's specific location using AI,
    and generate a human-readable text-only advisory summary.
    """
    import json
    farmer_info = farmer_info or {}
    admin = location_data.get("administrative", {})

    lat = float(location_data.get("latitude") or admin.get("lat") or 0.0)
    lon = float(location_data.get("longitude") or admin.get("lon") or 0.0)

    village = admin.get("village", "Local Area")
    raw_district = farmer_info.get("district") or admin.get("district") or ""
    district = resolve_district_name(raw_district, lat=lat, lon=lon)
    state = farmer_info.get("state") or admin.get("state", "Karnataka")

    soil = location_data.get("soil", {}).get("soil_type", "Loam")
    weather = location_data.get("weather_summary", {})
    current_season = weather.get("current_season", "Kharif (Monsoon)")
    avg_temp = float(weather.get("avg_max_temperature_c", 30.0))
    rain_mm = float(weather.get("forecast_next_7_days_rain_mm", 0.0))

    acres = float(farmer_info.get("acres") or location_data.get("land_acres") or 1.0)
    irrigation_str = str(farmer_info.get("irrigation", "Borewell / Irrigated"))

    # 1. Attempt dynamic AI evaluation via Groq LLM
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY", "")
        client = Groq(api_key=api_key)

        prompt_payload = {
            "latitude": lat,
            "longitude": lon,
            "village": village,
            "district": district,
            "state": state,
            "soil_type": soil,
            "season": current_season,
            "avg_temperature_c": avg_temp,
            "7_day_forecast_rain_mm": rain_mm,
            "cultivated_acres": acres,
            "water_source": irrigation_str
        }

        system_prompt = (
            "You are an expert Indian agronomist and decision-support specialist. "
            "Based strictly on the provided farm location and environmental parameters, dynamically determine "
            "ALL the possible crops that the farmer can realistically cultivate in this exact area across cereals, millets, pulses, oilseeds, cash crops, and vegetables. "
            "Do NOT limit the recommendations to only 3 crops. Provide a comprehensive list of all viable crops (aim for 6 to 10+ viable crops) ranked by overall suitability.\n\n"
            "Return valid JSON matching this schema:\n"
            "{\n"
            "  \"summary_text\": \"A comprehensive, clear text summary (plain text only, no markdown headers or asterisks) explaining the farm's location suitability, why these diverse crops can be grown, water and soil alignment, and rotation/intercropping management advice.\",\n"
            "  \"top_recommendations\": [\n"
            "    {\n"
            "      \"crop\": \"Crop Name\",\n"
            "      \"kannada_name\": \"Local Name\",\n"
            "      \"category\": \"Cereal / Pulse / Oilseed / Cash Crop / Vegetable\",\n"
            "      \"suitability\": \"Highly Suitable / Potentially Suitable\",\n"
            "      \"suitability_score\": 95,\n"
            "      \"duration_days\": \"105 - 120 days\",\n"
            "      \"water_needs\": \"350 - 450 mm (Low / Moderate / High)\",\n"
            "      \"reasons\": [\"Specific location and soil reason\"],\n"
            "      \"risks\": [\"Specific local risk\"]\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Location parameters:\n{json.dumps(prompt_payload, indent=2)}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=3000
        )

        ai_res = json.loads(resp.choices[0].message.content)
        ai_crops = ai_res.get("top_recommendations", [])
        ai_summary = ai_res.get("summary_text", "").strip()

        if ai_crops and len(ai_crops) >= 3 and ai_summary:
            # Normalize names
            for c in ai_crops:
                name = c.get("crop", "")
                if "Maize" in name or "Corn" in name:
                    c["crop"] = "Maize"
                elif "Rice" in name or "Paddy" in name:
                    c["crop"] = "Paddy"
                elif "Sorghum" in name or "Jowar" in name:
                    c["crop"] = "Jowar"
                elif "Pigeon Pea" in name or "Tur" in name:
                    c["crop"] = "Red Gram (Tur)"
                elif "Chickpea" in name or "Bengal Gram" in name:
                    c["crop"] = "Bengal Gram"
                elif "Finger Millet" in name or "Ragi" in name:
                    c["crop"] = "Ragi"

            # Ensure major traditional crops for the region are present if omitted
            crop_set = {c.get("crop") for c in ai_crops}
            if district in ("Dharwad", "Haveri", "Belagavi", "Davanagere") and "Maize" not in crop_set:
                ai_crops.insert(1, {
                    "crop": "Maize",
                    "kannada_name": "ಮೆಕ್ಕೆಜೋಳ (Mekke Jola)",
                    "category": "Cereal",
                    "suitability": "Highly Suitable",
                    "suitability_score": 92,
                    "duration_days": "90 - 110 days",
                    "water_needs": "500 - 650 mm (Moderate)",
                    "reasons": ["Premier commercial Kharif cereal in northern Karnataka transition zone."],
                    "risks": ["Susceptible to moisture logging and Fall Armyworm."]
                })

            return {
                "status": "success",
                "region_evaluated": f"{district}, {state}",
                "evaluated_season": current_season,
                "soil_evaluated": soil,
                "water_profile": irrigation_str,
                "summary_text": ai_summary,
                "top_recommendations": ai_crops,  # Return ALL possible crops identified by AI
                "all_ranked_crops": ai_crops,
                "total_crops_found": len(ai_crops),
                "disclaimer": "Comprehensive list of all viable crops dynamically evaluated by AI based on regional agro-climatic conditions and location indicators."
            }
    except Exception:
        pass

    # Heuristic fallback if AI service is temporarily offline or in unit testing
    candidates: List[Dict[str, Any]] = []
    has_irrigation = "rainfed" not in irrigation_str.lower()
    for crop_name in VERIFIED_CROP_RULES.keys():
        if crop_name == "Rice":
            continue

        eval_res = evaluate_crop_suitability(
            crop_name=crop_name,
            soil_type=soil,
            district=district,
            current_season=current_season,
            avg_max_temp=avg_temp,
            has_irrigation=has_irrigation
        )
        candidates.append(eval_res)

    candidates.sort(key=lambda x: x["suitability_score"], reverse=True)
    # Return all viable crops with suitability score >= 55, or at least top 6
    viable_candidates = [c for c in candidates if c["suitability_score"] >= 55]
    top_recs = viable_candidates if len(viable_candidates) >= 5 else candidates[:8]

    summary_text = (
        f"Farm Location Summary for {district}, {state}:\n"
        f"The farm is situated at coordinates ({lat:.4f}°N, {lon:.4f}°E) with {soil} soil and {irrigation_str} water profile. "
        f"Under current {current_season} conditions (temperature around {avg_temp}°C), a diverse range of crops can be "
        f"successfully grown in this agro-climatic zone: {', '.join([c['crop'] for c in top_recs])}. "
        f"These crops match local soil moisture retention, historical rainfall patterns, and regional APMC mandi demand. "
        f"Recommended management: practice intercropping and crop rotation (e.g., cereals rotated with pulses like red gram or chickpea) "
        f"to preserve soil fertility, break pest cycles, and diversify household farm income."
    )

    return {
        "status": "success",
        "region_evaluated": f"{district}, {state}",
        "evaluated_season": current_season,
        "soil_evaluated": soil,
        "water_profile": "Irrigated" if has_irrigation else "Rainfed",
        "summary_text": summary_text,
        "top_recommendations": top_recs,  # Return ALL viable crops
        "all_ranked_crops": candidates,
        "total_crops_found": len(top_recs),
        "disclaimer": "Comprehensive list of all viable crops evaluated according to regional agro-climatic zones and local mandi crop statistics."
    }


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from location_service import analyze_farm_location

    test_districts = [
        ("Kalaburagi", 17.3297, 76.8343),
        ("Mandya", 12.5229, 76.8978),
        ("Dharwad", 15.4589, 75.0078),
        ("Vijayapura", 16.8302, 75.7100),
        ("Kolar", 13.1367, 78.1291),
        ("Udupi", 13.3409, 74.7421)
    ]

    print("=== Testing Location-Specific Recommendations Across Districts ===")
    for name, lat, lon in test_districts:
        loc = analyze_farm_location(lat, lon, acres=2.5)
        recs = recommend_crops(loc, {"irrigation": "Borewell / Irrigated", "district": name})
        top_crops = [f"{r['crop']} ({r['suitability_score']})" for r in recs["top_recommendations"]]
        print(f"\n📍 {name}: {', '.join(top_crops)}")
