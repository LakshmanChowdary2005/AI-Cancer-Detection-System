"""
utils/health_guidance.py
------------------------
Clinical knowledge base providing stage-specific supportive remedies, daily
health habits, clinical nutrition, precautions, and organ-tailored guidance
for cancer patients and routine surveillance individuals.
"""

from typing import Dict, Any, List

# Stage normalization helper
def normalize_stage(stage_str: str) -> str:
    s = (stage_str or "").strip().lower()
    if "0" in s or "zero" in s or "benign" in s or "normal" in s:
        return "Stage 0"
    if "iv" in s or "4" in s:
        return "Stage IV"
    if "iii" in s or "3" in s:
        return "Stage III"
    if "ii" in s or "2" in s:
        return "Stage II"
    if "i" in s or "1" in s:
        return "Stage I"
    return "Stage 0"


# Stage-specific guidance dictionary
STAGE_GUIDANCE_DATA = {
    "Stage 0": {
        "stage_title": "Stage 0 (Benign / In-Situ / Preventive Surveillance)",
        "clinical_goal": "Maintain optimal tissue health, reinforce primary and secondary cancer prevention, reduce systemic oxidative stress, and sustain routine screening vigilance.",
        "remedies": [
            {
                "title": "Natural Anti-Inflammatory Teas",
                "desc": "Consume freshly brewed green tea (rich in EGCG polyphenols), chamomile, or ginger root infusion daily to reduce systemic oxidative markers."
            },
            {
                "title": "Tissue Barrier Protection & Moisture Care",
                "desc": "Apply fragrance-free mineral barrier creams with ceramides and pure aloe vera to soothe skin and mucous tissues from environmental stressors."
            },
            {
                "title": "Natural Antioxidant Polyphenol Regimen",
                "desc": "Incorporate cold-pressed extra virgin olive oil, wild blueberries, flaxseed meal, and turmeric with a pinch of black pepper into daily meals."
            },
            {
                "title": "Electrolyte & Cellular Hydration",
                "desc": "Drink filtered water infused with lemon or cucumber and tender coconut water to support efficient cellular detoxification and kidney clearance."
            }
        ],
        "health_habits": [
            {
                "title": "150+ Minutes of Weekly Aerobic Exercise",
                "desc": "Engage in moderate-intensity physical activity (brisk walking, swimming, cycling) for at least 30 minutes, 5 days per week to optimize immune function."
            },
            {
                "title": "Circadian Rest & Sleep Rhythm",
                "desc": "Maintain 7 to 8 hours of uninterrupted nocturnal sleep in a dark, cool room to regulate natural melatonin production and DNA repair enzymes."
            },
            {
                "title": "Adherence to Screening Guidelines",
                "desc": "Schedule age-appropriate mammograms, dermatological skin checks, low-dose CT (if indicated), or colonoscopy per USPSTF/ACS schedules."
            },
            {
                "title": "Stress Reduction & Cortisol Modulation",
                "desc": "Practice 15 minutes of mindfulness meditation, diaphragmatic breathing exercises, or restorative yoga daily to mitigate chronic stress hormones."
            }
        ],
        "nutrition": [
            {
                "title": "Mediterranean Anti-Inflammatory Diet",
                "desc": "Emphasize high-fiber plant foods, cruciferous vegetables (broccoli, Brussels sprouts), legumes, walnuts, and wild-caught fatty fish."
            },
            {
                "title": "Hydration Benchmark",
                "desc": "Target 2.5 to 3.0 liters of pure water daily; limit caffeine intake and avoid artificially sweetened beverages."
            },
            {
                "title": "Gut Microbiome Diversity",
                "desc": "Incorporate prebiotic foods (garlic, onions, oats, asparagus) and natural fermented probiotics (kefir, yogurt) to reinforce gut-associated lymphoid tissue."
            }
        ],
        "precautions": [
            {
                "title": "Zero Tobacco & Nicotine Exposure",
                "desc": "Strictly avoid all forms of smoking, vaping, chewing tobacco, and passive secondhand smoke to eliminate direct mutagenic carcinogens."
            },
            {
                "title": "Limit or Eliminate Alcohol",
                "desc": "Restrict alcohol intake strictly; alcohol breaks down into acetaldehyde, a potent Group 1 carcinogen that elevates cancer risks."
            },
            {
                "title": "Avoid Processed Meats & Nitrates",
                "desc": "Avoid charbroiled red meats, bacon, sausages, and ultra-processed foods containing artificial nitrate preservatives."
            }
        ]
    },

    "Stage I": {
        "stage_title": "Stage I (Early-Stage Localized Malignancy)",
        "clinical_goal": "Enhance body resilience for primary local intervention (surgery or targeted ablation), accelerate post-procedure tissue healing, maintain nutritional stamina, and control early fatigue.",
        "remedies": [
            {
                "title": "Gentle Nausea & Digestive Soothing",
                "desc": "Sip fresh ginger tea or warm peppermint infusions; utilize P6 acupressure wrist bands or mild lemon aromatherapy for procedure-related dyspepsia."
            },
            {
                "title": "Wound Care & Sterile Healing Barrier",
                "desc": "Clean biopsy and surgical sites strictly with sterile saline; apply physician-approved silicone scar gel or medical dressings; avoid submerging in baths."
            },
            {
                "title": "Cool Compress for Localized Swelling",
                "desc": "Apply clean cool compresses (15 minutes on, 15 minutes off) wrapped in sterile gauze to reduce post-biopsy edema and local inflammation."
            },
            {
                "title": "Oral Hygiene with Baking Soda Rinse",
                "desc": "Rinse mouth 3-4 times daily with a mild solution of 1/2 tsp baking soda and 1/2 tsp sea salt in warm water to prevent microbial oral imbalance."
            }
        ],
        "health_habits": [
            {
                "title": "Gentle Restorative Walking",
                "desc": "Perform 20 to 30 minutes of low-impact walking daily, divided into two manageable sessions to promote vascular return and prevent venous thromboembolism."
            },
            {
                "title": "Strategic Energy Conservation",
                "desc": "Pace daily activities; tackle higher-effort tasks during peak morning energy windows and take a planned 20-minute restorative afternoon rest."
            },
            {
                "title": "Meticulous Hand Hygiene & Infection Shield",
                "desc": "Wash hands frequently with antimicrobial soap; avoid crowded unventilated spaces to protect the immune system during diagnostic procedures."
            },
            {
                "title": "Symptom & Distress Journaling",
                "desc": "Track daily pain scores (0-10), fatigue levels, and emotional wellness using a daily journal or app to discuss proactively with your care team."
            }
        ],
        "nutrition": [
            {
                "title": "High-Quality Protein for Tissue Repair",
                "desc": "Target 1.2–1.5 grams of protein per kilogram of body weight (eggs, lean poultry, lentils, organic tofu, pea protein) to rebuild cellular integrity."
            },
            {
                "title": "Frequent Small Nutrient-Dense Meals",
                "desc": "Consume 5 to 6 small meals throughout the day instead of 3 large heavy meals to optimize gastrointestinal digestion and nutrient absorption."
            },
            {
                "title": "Electrolyte-Rich Hydration",
                "desc": "Drink 2.5 liters of fluids daily including clear bone/vegetable broths, coconut water, and dilute electrolyte solutions."
            }
        ],
        "precautions": [
            {
                "title": "Avoid Unvetted High-Dose Megavitamins",
                "desc": "Do not self-prescribe high-dose antioxidant pills (e.g., massive vitamin E/A doses) without oncologist clearance, as they can interfere with planned therapies."
            },
            {
                "title": "Avoid Vigorous Strenuous Straining",
                "desc": "Avoid heavy weightlifting (>10 lbs) or high-intensity abdominal strain until your surgical team confirms wound tensile healing."
            },
            {
                "title": "Avoid Raw or Undercooked Foods",
                "desc": "Ensure all animal proteins and eggs are thoroughly cooked; thoroughly wash all raw fruits and vegetables to prevent foodborne pathogens."
            }
        ]
    },

    "Stage II": {
        "stage_title": "Stage II (Locally Advanced / Regional Focus)",
        "clinical_goal": "Mitigate treatment-induced side effects (chemotherapy/radiation/surgery), prevent treatment interruptions, maintain muscular mass, and support immune resilience.",
        "remedies": [
            {
                "title": "Mucositis & Oral Mucosa Protection",
                "desc": "Gargle with warm salt-baking soda solution (1/2 tsp salt + 1/2 tsp baking soda in 250ml warm water) after every meal; avoid alcohol-based mouthwashes."
            },
            {
                "title": "Radiation & Chemo Skin Soothing",
                "desc": "Apply oncologist-approved calendula cream, pure aloe, or hyaluronic barrier dressings to irradiated or irritated skin areas; avoid harsh soaps and friction."
            },
            {
                "title": "Aromatherapy & Herbal Anti-Emetic Support",
                "desc": "Inhale chilled lemon or peppermint vapors; chew small amounts of candied ginger or sip ginger-mint infusions 30 minutes before meals."
            },
            {
                "title": "Peripheral Neuropathy Comfort",
                "desc": "Keep extremities warm with soft non-binding cotton socks and gloves; gently massage hands and feet with arnica or unscented vitamin E oil."
            }
        ],
        "health_habits": [
            {
                "title": "Structured Low-Intensity Movement",
                "desc": "Perform 15-20 minutes of light walking or seated resistance band routines daily to stimulate lymphatic circulation and counteract cancer-related fatigue."
            },
            {
                "title": "Twice-Daily Body Temperature Monitoring",
                "desc": "Record body temperature morning and evening. Immediately contact your oncology triage if temperature reaches or exceeds 38.0°C (100.4°F)."
            },
            {
                "title": "Proactive Lymphedema Prevention",
                "desc": "Elevate the limb corresponding to treated lymph nodes when resting; avoid tight clothing, blood pressure cuffs, or needle sticks on the affected limb."
            },
            {
                "title": "Cognitive & Emotional Relaxation",
                "desc": "Practice 20 minutes of guided progressive muscle relaxation or listen to binaural soundscapes to reduce procedural anxiety and improve sleep quality."
            }
        ],
        "nutrition": [
            {
                "title": "Caloric & Protein Fortification",
                "desc": "Blend high-calorie, nutrient-dense smoothies with whey or plant protein, avocado, ripe bananas, almond butter, and oat milk if appetite decreases."
            },
            {
                "title": "Easy-to-Digest, Bland Foods",
                "desc": "Focus on oatmeal, cooked sweet potatoes, steamed rice, scrambled eggs, and tender carrots during days of gastrointestinal sensitivity."
            },
            {
                "title": "Continuous Sip Hydration",
                "desc": "Keep a water flask at bedside; take small sips every 15 minutes to prevent dehydration-induced fatigue and flush chemotherapy metabolites."
            }
        ],
        "precautions": [
            {
                "title": "Zero Alcohol & Blood-Thinning Supplements",
                "desc": "Strictly avoid alcoholic beverages and unapproved herbal supplements like Ginkgo Biloba, St. John's Wort, or high-dose fish oil during therapy cycles."
            },
            {
                "title": "Infection Precautions (Neutropenia Awareness)",
                "desc": "Wear a well-fitted mask in public; avoid contact with sick household members; avoid handling pet litter, fresh soil, or live plants."
            },
            {
                "title": "Protect Skin from UV & Extreme Temperatures",
                "desc": "Shield treated skin from direct sun exposure with UPF 50+ clothing; avoid hot tubs, saunas, and ice packs directly on radiated fields."
            }
        ]
    },

    "Stage III": {
        "stage_title": "Stage III (Locally Advanced / Regional Lymph Node Involvement)",
        "clinical_goal": "Maximize systemic therapy tolerance, counter cancer cachexia and muscle loss, maintain strict neutropenic hygiene, and enhance comprehensive supportive care.",
        "remedies": [
            {
                "title": "Thermal Sensitivity & Neuropathy Relief",
                "desc": "Avoid touching cold metal surfaces or drinking ice-cold liquids if receiving oxaliplatin/taxanes; wear soft thermal gloves when opening the refrigerator."
            },
            {
                "title": "Cancer Fatigue & Circadian Light Therapy",
                "desc": "Expose eyes to natural indirect morning sunlight for 10-15 minutes within 1 hour of waking to anchor the circadian clock and optimize nighttime rest."
            },
            {
                "title": "Digestive Regularity & Constipation Remedy",
                "desc": "Consume warm prune juice, stewed apples with cinnamon, and soluble psyllium husk; ensure adequate hydration to counter antiemetic/opioid constipation."
            },
            {
                "title": "Non-Pharmacological Pain & Tension Relief",
                "desc": "Utilize warm (not hot) compresses on tense muscles, gentle head/shoulder acupressure, and guided visualization recordings to diminish pain perception."
            }
        ],
        "health_habits": [
            {
                "title": "Supervised Rehabilitation & Sarcopenia Defense",
                "desc": "Perform gentle range-of-motion stretching and supervised light chair squats/stands to preserve skeletal muscle mass and functional independence."
            },
            {
                "title": "Rigorous Neutropenic Hygiene Protocol",
                "desc": "Sanitize food preparation surfaces with food-grade disinfectants; ensure all meals are freshly prepared and thoroughly steamed; avoid buffets."
            },
            {
                "title": "Multidisciplinary Telemetry Logging",
                "desc": "Log daily weight, fluid intake, bowel habits, and pain scores (1-10) in your patient portal for immediate nurse navigator review."
            },
            {
                "title": "Palliative & Psychosocial Support Engagement",
                "desc": "Meet regularly with an oncology clinical dietitian, oncology social worker, and supportive palliative care specialist to optimize quality of life."
            }
        ],
        "nutrition": [
            {
                "title": "Anti-Cachexia High-Calorie Nutrition",
                "desc": "Incorporate healthy caloric boosters (avocado oil drizzles, nut butter dollops, full-fat Greek yogurt, coconut cream) into every meal."
            },
            {
                "title": "Warm Bone & Mineral Broths",
                "desc": "Drink warm simmered bone or vegetable broths seasoned with sea salt and fresh ginger to restore electrolytes and soothe gastrointestinal linings."
            },
            {
                "title": "Enzyme & Digestion Support",
                "desc": "Eat small portions slowly in an upright seated posture; include well-tolerated digestive aids like papaya, stewed pears, or warm lemon water."
            }
        ],
        "precautions": [
            {
                "title": "Strict Avoidance of Crowds during Nadir",
                "desc": "Stay away from crowded indoor public venues during chemotherapy nadir (typically days 7 through 14 post-infusion when white blood cells drop)."
            },
            {
                "title": "Do Not Take NSAIDs Without Oncologist Approval",
                "desc": "Avoid aspirin, ibuprofen, and naproxen unless cleared by your physician, as they can impair platelet function and irritate gastric linings."
            },
            {
                "title": "Avoid Unpasteurized Juices & Soft Cheeses",
                "desc": "Avoid raw unpasteurized milk, soft cheeses (brie, camembert), deli meats, and raw sprouts due to the risk of listeria and salmonella infections."
            }
        ]
    },

    "Stage IV": {
        "stage_title": "Stage IV (Advanced / Metastatic / Comprehensive Supportive Care)",
        "clinical_goal": "Maximize comfort, preserve functional dignity and vitality, manage complex symptoms proactively, support organ function, and provide holistic multidisciplinary care.",
        "remedies": [
            {
                "title": "Dyspnea & Respiratory Comfort",
                "desc": "Use a cool-mist bedside humidifier; direct a gentle handheld fan across the face and nose to stimulate trigeminal nerve receptors and relieve breathlessness."
            },
            {
                "title": "Xerostomia & Dry Mouth Soothing",
                "desc": "Sip ice chips, suck on sugar-free lemon/tart candies, or apply physician-prescribed oral artificial saliva sprays to soothe oral mucosal dryness."
            },
            {
                "title": "Comfort Positioning & Pressure Relief",
                "desc": "Utilize ergonomic memory-foam body pillows, wedge cushions, and alternating pressure mattress toppers to alleviate pressure points and bone aches."
            },
            {
                "title": "Mild Aromatherapy for Nausea & Serenity",
                "desc": "Diffuse 2-3 drops of natural lavender, sweet orange, or bergamot essential oils in the living area to create a calm, nausea-reducing sensory environment."
            }
        ],
        "health_habits": [
            {
                "title": "Comfort-First Flexible Movement",
                "desc": "Engage in gentle seated or in-bed leg extensions, arm circles, and short supported strolls; always rest before fatigue becomes overwhelming."
            },
            {
                "title": "Empowered Autonomy & Rest Pacing",
                "desc": "Structure the day around personal priorities, joy, and comfort; take multiple short rests whenever desired without rigid schedules."
            },
            {
                "title": "Skin Integrity & Barrier Inspection",
                "desc": "Inspect skin daily for pressure redness; apply thick moisturizing emollient ointments and gently reposition every 2 hours if resting in bed."
            },
            {
                "title": "Holistic Supportive & Spiritual Care",
                "desc": "Connect with palliative supportive care counselors, family members, oncology therapists, or spiritual advisors for deep emotional peace."
            }
        ],
        "nutrition": [
            {
                "title": "Pleasure & Comfort-Oriented Nutrition",
                "desc": "Focus on foods the patient genuinely enjoys; serve favorite puddings, milkshakes, custards, or pureed soups in small, attractive portions."
            },
            {
                "title": "Frequent Hydrating Sips",
                "desc": "Offer small, chilled sips of electrolyte water, fruit-infused water, popsicles, or watermelon slices rather than insisting on full glasses."
            },
            {
                "title": "Gentle, Non-Aromatic Meals",
                "desc": "Serve foods at room temperature or cool to minimize strong cooking odors that can trigger reflex nausea."
            }
        ],
        "precautions": [
            {
                "title": "Urgent Red-Flag Symptom Reporting",
                "desc": "Immediately notify your oncology palliative team for fever (>38°C), sudden shortness of breath, acute new severe bone pain, or acute confusion."
            },
            {
                "title": "Fall Prevention & Home Safety",
                "desc": "Ensure walking paths are clear of rugs and cords; install bathroom grab bars and use nightlights to prevent balance-related falls."
            },
            {
                "title": "Never Force Large Meals",
                "desc": "Do not force food consumption if appetite is absent; honor natural physiological cues to prevent vomiting, aspiration, and distress."
            }
        ]
    }
}


# Cancer-type specific remedies and precautions
CANCER_TYPE_GUIDANCE = {
    "brain": {
        "title": "Brain Tumor Supportive Focus",
        "icon": "fa-solid fa-brain",
        "guidance": [
            "Maintain head elevation at 30 degrees during sleep to reduce intracranial pressure and morning headache.",
            "Minimize high-intensity blue light, loud sensory environments, and prolonged screen time to mitigate cognitive fatigue.",
            "Adhere strictly to anti-epileptic medication schedules if prescribed; follow seizure precautions (shower instead of tub bath).",
            "Engage in cognitive pacing: break mentally taxing tasks into 15-minute segments followed by quiet brain rest."
        ]
    },
    "breast": {
        "title": "Breast Cancer Supportive Focus",
        "icon": "fa-solid fa-ribbon",
        "guidance": [
            "Prevent lymphedema on the operated side: avoid blood pressure cuffs, blood draws, and tight constricting jewelry on that arm.",
            "Wear soft, seamless, front-closure cotton bras without underwires to prevent friction on incision or radiation sites.",
            "Perform gentle postoperative arm wall-climbing and shoulder mobility exercises twice daily once cleared by the surgeon.",
            "Apply physician-approved unscented silicone gel or pure calendula ointment to radiation fields only after daily therapy."
        ]
    },
    "lung": {
        "title": "Lung Cancer Supportive Focus",
        "icon": "fa-solid fa-lungs",
        "guidance": [
            "Practice pursed-lip and diaphragmatic breathing exercises for 10 minutes twice daily to expand tidal volume and oxygen saturation.",
            "Maintain a HEPA-filtered clean-air bedroom environment; strictly avoid aerosol sprays, incense, wood smoke, and strong cleaning chemicals.",
            "Use warm steam inhalation with a drop of eucalyptus oil or a cool-mist humidifier to loosen bronchial secretions.",
            "Sleep with torso gently elevated (using 2 pillows or a wedge) to ease nocturnal airway clearance and prevent coughing spells."
        ]
    },
    "skin": {
        "title": "Skin Cancer Supportive Focus",
        "icon": "fa-solid fa-sun",
        "guidance": [
            "Apply broad-spectrum mineral sunscreen (Zinc Oxide / Titanium Dioxide SPF 50+) daily even on cloudy days and indoors near windows.",
            "Wear certified UPF 50+ wide-brimmed hats (at least 3-inch brim), UV-blocking sunglasses, and tightly woven protective long sleeves.",
            "Perform monthly ABCDE self-skin examinations (Asymmetry, Border, Color, Diameter, Evolving) and photograph suspicious lesions.",
            "Avoid peak solar hours (10:00 AM to 4:00 PM); seek shade and strictly avoid all commercial tanning beds or UV nail curing lamps."
        ]
    }
}


def get_stage_guidance(stage: str, cancer_type: str = "general", language: str = "en") -> Dict[str, Any]:
    """
    Returns structured supportive care, remedies, healthy habits, nutrition,
    precautions, and organ-tailored guidance based on cancer stage and cancer type.
    """
    norm_stage = normalize_stage(stage)
    base = STAGE_GUIDANCE_DATA.get(norm_stage, STAGE_GUIDANCE_DATA["Stage 0"])

    ctype = (cancer_type or "general").strip().lower()
    organ_key = None
    if "brain" in ctype:
        organ_key = "brain"
    elif "breast" in ctype:
        organ_key = "breast"
    elif "lung" in ctype:
        organ_key = "lung"
    elif "skin" in ctype:
        organ_key = "skin"

    organ_info = CANCER_TYPE_GUIDANCE.get(organ_key) if organ_key else None

    guidance = {
        "stage": norm_stage,
        "cancer_type": ctype,
        "stage_title": base["stage_title"],
        "clinical_goal": base["clinical_goal"],
        "remedies": [dict(r) for r in base["remedies"]],
        "health_habits": [dict(h) for h in base["health_habits"]],
        "nutrition": [dict(n) for n in base["nutrition"]],
        "precautions": [dict(p) for p in base["precautions"]],
        "organ_specific": dict(organ_info) if organ_info else None,
        "disclaimer": (
            "Medical Disclaimer: These remedies and health habits are evidence-based complementary supportive guidelines. "
            "They are formulated to support the patient's general wellbeing, comfort, and recovery alongside medical care. "
            "They do not replace clinical diagnosis, surgery, systemic chemotherapy, radiotherapy, or personalized instructions "
            "prescribed by the treating oncologist."
        ),
        "_lang": "en"
    }

    if language and language != "en":
        try:
            return translate_stage_guidance(guidance, language)
        except Exception:
            return guidance

    return guidance


def translate_stage_guidance(guidance: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
    """
    Translates the text fields of stage guidance into the target language using
    translate_text_batch / translate_text.
    """
    if not guidance or target_lang == "en":
        return guidance

    try:
        from utils.translator import translate_text, translate_text_batch
    except Exception:
        return guidance

    import copy
    result = copy.deepcopy(guidance)
    result["_lang"] = target_lang

    # Collect all strings to translate
    strings_to_translate: List[str] = [
        result.get("stage_title", ""),
        result.get("clinical_goal", ""),
        result.get("disclaimer", "")
    ]

    for item in result.get("remedies", []):
        strings_to_translate.extend([item.get("title", ""), item.get("desc", "")])
    for item in result.get("health_habits", []):
        strings_to_translate.extend([item.get("title", ""), item.get("desc", "")])
    for item in result.get("nutrition", []):
        strings_to_translate.extend([item.get("title", ""), item.get("desc", "")])
    for item in result.get("precautions", []):
        strings_to_translate.extend([item.get("title", ""), item.get("desc", "")])

    organ = result.get("organ_specific")
    if organ:
        strings_to_translate.append(organ.get("title", ""))
        strings_to_translate.extend(organ.get("guidance", []))

    # Clean and warm translation cache
    unique_strings = [s for s in dict.fromkeys(strings_to_translate) if s and isinstance(s, str)]
    try:
        translate_text_batch(unique_strings, target_lang=target_lang)
    except Exception:
        pass

    # Map translations
    def tr_s(text: str) -> str:
        if not text:
            return text
        try:
            return translate_text(text, target_lang)
        except Exception:
            return text

    result["stage_title"] = tr_s(result.get("stage_title", ""))
    result["clinical_goal"] = tr_s(result.get("clinical_goal", ""))
    result["disclaimer"] = tr_s(result.get("disclaimer", ""))

    for item in result.get("remedies", []):
        item["title"] = tr_s(item.get("title", ""))
        item["desc"] = tr_s(item.get("desc", ""))

    for item in result.get("health_habits", []):
        item["title"] = tr_s(item.get("title", ""))
        item["desc"] = tr_s(item.get("desc", ""))

    for item in result.get("nutrition", []):
        item["title"] = tr_s(item.get("title", ""))
        item["desc"] = tr_s(item.get("desc", ""))

    for item in result.get("precautions", []):
        item["title"] = tr_s(item.get("title", ""))
        item["desc"] = tr_s(item.get("desc", ""))

    if result.get("organ_specific"):
        org = result["organ_specific"]
        org["title"] = tr_s(org.get("title", ""))
        org["guidance"] = [tr_s(g) for g in org.get("guidance", [])]

    return result
