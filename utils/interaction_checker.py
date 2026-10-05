"""
utils/interaction_checker.py
----------------------------
Comprehensive Clinical Oncology Medication & Supplement Interaction Engine.
Analyzes pharmacokinetic (CYP450, P-gp, renal clearance) and pharmacodynamic
interactions between chemotherapy, targeted immunotherapy, supportive drugs,
and dietary/herbal supplements.
"""

from typing import List, Dict, Any, Optional

# Database of oncology drugs, supportive medications, and herbal supplements
DRUG_DATABASE: List[Dict[str, Any]] = [
    # --- Chemotherapy Agents ---
    {
        "id": "cisplatin",
        "name": "Cisplatin",
        "category": "Chemotherapy",
        "class": "Platinum Alkylating Agent",
        "cyp_enzymes": [],
        "clearance": "Renal",
        "toxicity_profile": ["Nephrotoxicity", "Ototoxicity", "Emetogenic", "Myelosuppression"],
        "description": "Potent platinum agent used in lung, ovarian, testicular, and bladder cancers."
    },
    {
        "id": "carboplatin",
        "name": "Carboplatin",
        "category": "Chemotherapy",
        "class": "Platinum Agent",
        "cyp_enzymes": [],
        "clearance": "Renal",
        "toxicity_profile": ["Thrombocytopenia", "Myelosuppression", "Nephrotoxicity (mild)"],
        "description": "Standard platinum derivative widely prescribed in lung, ovarian, and breast cancers."
    },
    {
        "id": "paclitaxel",
        "name": "Paclitaxel (Taxol)",
        "category": "Chemotherapy",
        "class": "Taxane",
        "cyp_enzymes": ["CYP2C8", "CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Peripheral Neuropathy", "Neutropenia", "Hypersensitivity"],
        "description": "Microtubule stabilizer indicated for breast, ovarian, and lung malignancies."
    },
    {
        "id": "docetaxel",
        "name": "Docetaxel (Taxotere)",
        "category": "Chemotherapy",
        "class": "Taxane",
        "cyp_enzymes": ["CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Fluid Retention", "Neutropenia", "Neuropathy"],
        "description": "Semisynthetic taxane active in prostate, breast, and non-small cell lung cancer."
    },
    {
        "id": "doxorubicin",
        "name": "Doxorubicin (Adriamycin)",
        "category": "Chemotherapy",
        "class": "Anthracycline",
        "cyp_enzymes": ["CYP3A4", "CYP2D6"],
        "clearance": "Biliary / Hepatic",
        "toxicity_profile": ["Cardiotoxicity", "Severe Myelosuppression", "Alopecia", "Extravasation"],
        "description": "Topoisomerase II inhibitor and reactive oxygen producer; backbone in lymphoma and breast cancer."
    },
    {
        "id": "5fu",
        "name": "5-Fluorouracil (5-FU)",
        "category": "Chemotherapy",
        "class": "Antimetabolite (Fluoropyrimidine)",
        "cyp_enzymes": ["DPD metabolism"],
        "clearance": "Hepatic / Catabolic",
        "toxicity_profile": ["Mucositis", "Diarrhea", "Hand-Foot Syndrome", "Coronary Vasospasm"],
        "description": "Pyrimidine analogue used in colorectal, breast, gastric, and head/neck cancers."
    },
    {
        "id": "temozolomide",
        "name": "Temozolomide (Temodar)",
        "category": "Chemotherapy",
        "class": "Alkylating Agent (Imidazotetrazine)",
        "cyp_enzymes": [],
        "clearance": "Spontaneous chemical hydrolysis",
        "toxicity_profile": ["Myelosuppression", "Nausea", "Fatigue", "Hepatotoxicity"],
        "description": "Oral alkylating agent capable of crossing the blood-brain barrier for Glioblastoma."
    },
    {
        "id": "methotrexate",
        "name": "Methotrexate",
        "category": "Chemotherapy",
        "class": "Antifolate",
        "cyp_enzymes": [],
        "clearance": "Renal (Organic Anion Transporter)",
        "toxicity_profile": ["Severe Mucositis", "Myelosuppression", "Nephrotoxicity", "Hepatotoxicity"],
        "description": "Dihydrofolate reductase inhibitor used in leukemias, lymphomas, and osteosarcoma."
    },

    # --- Targeted & Hormonal Therapies ---
    {
        "id": "tamoxifen",
        "name": "Tamoxifen",
        "category": "Hormonal Therapy",
        "class": "SERM (Selective Estrogen Receptor Modulator)",
        "cyp_enzymes": ["CYP2D6 (prodrug to Endoxifen)", "CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Thromboembolism", "Hot Flashes", "Endometrial Hyperplasia"],
        "description": "Requires active CYP2D6 bioactivation into Endoxifen to prevent breast cancer recurrence."
    },
    {
        "id": "letrozole",
        "name": "Letrozole (Femara)",
        "category": "Hormonal Therapy",
        "class": "Aromatase Inhibitor",
        "cyp_enzymes": ["CYP3A4", "CYP2A6"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Arthralgia", "Bone Demineralization / Osteoporosis", "Fatigue"],
        "description": "Non-steroidal aromatase inhibitor for postmenopausal hormone-receptor positive breast cancer."
    },
    {
        "id": "osimertinib",
        "name": "Osimertinib (Tagrisso)",
        "category": "Targeted Therapy",
        "class": "3rd-Gen EGFR Tyrosine Kinase Inhibitor",
        "cyp_enzymes": ["CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["QTc Prolongation", "Cardiomyopathy", "Interstitial Lung Disease", "Diarrhea"],
        "description": "Indicated in EGFR-mutant (T790M) non-small cell lung carcinoma."
    },
    {
        "id": "trastuzumab",
        "name": "Trastuzumab (Herceptin)",
        "category": "Targeted Therapy",
        "class": "Anti-HER2 Monoclonal Antibody",
        "cyp_enzymes": [],
        "clearance": "Reticuloendothelial catabolism",
        "toxicity_profile": ["Cardiotoxicity (Decreased LVEF)", "Infusion Reactions"],
        "description": "Monoclonal antibody targeting human epidermal growth factor receptor 2 in breast/gastric cancer."
    },
    {
        "id": "pembrolizumab",
        "name": "Pembrolizumab (Keytruda)",
        "category": "Immunotherapy",
        "class": "PD-1 Immune Checkpoint Inhibitor",
        "cyp_enzymes": [],
        "clearance": "Non-specific catabolism",
        "toxicity_profile": ["Immune-Related Adverse Events (irAEs)", "Pneumonitis", "Colitis", "Thyroiditis"],
        "description": "Restores anti-tumor T-cell immunity across melanoma, lung, and MSI-high solid tumors."
    },

    # --- Supportive Oncology Prescription Drugs ---
    {
        "id": "ondansetron",
        "name": "Ondansetron (Zofran)",
        "category": "Supportive Care",
        "class": "5-HT3 Receptor Antagonist",
        "cyp_enzymes": ["CYP3A4", "CYP1A2", "CYP2D6"],
        "clearance": "Hepatic",
        "toxicity_profile": ["QTc Prolongation", "Constipation", "Headache"],
        "description": "First-line antiemetic for chemotherapy-induced nausea and vomiting."
    },
    {
        "id": "dexamethasone",
        "name": "Dexamethasone",
        "category": "Supportive Care",
        "class": "Corticosteroid",
        "cyp_enzymes": ["CYP3A4 (substrate & mild inducer)"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Hyperglycemia", "Immunosuppression", "Insomnia", "Gastric Ulcers"],
        "description": "Anti-edema and anti-emetic corticosteroid used routinely in brain edema and chemotherapy protocols."
    },
    {
        "id": "omeprazole",
        "name": "Omeprazole / PPIs",
        "category": "Prescription OTC",
        "class": "Proton Pump Inhibitor",
        "cyp_enzymes": ["CYP2C19", "CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Gastric Acid Suppression", "Hypomagnesemia"],
        "description": "Alters gastric pH which significantly impairs oral absorption of many targeted kinase inhibitors."
    },
    {
        "id": "warfarin",
        "name": "Warfarin / Blood Thinners",
        "category": "Prescription OTC",
        "class": "Anticoagulant (Vitamin K Antagonist)",
        "cyp_enzymes": ["CYP2C9", "CYP3A4", "CYP1A2"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Hemorrhage / Bleeding", "Narrow Therapeutic Index"],
        "description": "Requires strict INR monitoring; highly vulnerable to food and herbal metabolic interactions."
    },
    {
        "id": "ibuprofen",
        "name": "Ibuprofen / NSAIDs",
        "category": "Prescription OTC",
        "class": "Non-Steroidal Anti-Inflammatory Drug",
        "cyp_enzymes": ["CYP2C9"],
        "clearance": "Renal",
        "toxicity_profile": ["Gastrointestinal Bleeding", "Nephrotoxicity", "Platelet Inhibition"],
        "description": "Competes with renal clearance of antimetabolites like methotrexate."
    },

    # --- Herbal Remedies & Dietary Supplements ---
    {
        "id": "st_johns_wort",
        "name": "St. John's Wort (Hypericum perforatum)",
        "category": "Herbal Supplement",
        "class": "Potent CYP3A4 & P-gp Inducer",
        "cyp_enzymes": ["Potent CYP3A4 Inducer", "P-gp Inducer"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Drug Level Clearance / Efficacy Failure", "Serotonin Syndrome"],
        "description": "Herbal mood remedy; causes catastrophic drop in systemic drug levels of chemotherapy and kinase inhibitors."
    },
    {
        "id": "curcumin",
        "name": "Curcumin / Turmeric Extract (High Dose)",
        "category": "Herbal Supplement",
        "class": "Polyphenol / Mild CYP Inhibitor & Antiplatelet",
        "cyp_enzymes": ["CYP3A4 (mild)", "CYP2C9 (mild)", "CYP2D6 (mild)"],
        "clearance": "Hepatic / Glucuronidation",
        "toxicity_profile": ["Antiplatelet Effect", "Mild CYP Modulation", "GI Upset"],
        "description": "High-dose extract inhibits platelet aggregation and weakly competes with CYP2D6/CYP3A4 substrates."
    },
    {
        "id": "green_tea_extract",
        "name": "Green Tea Extract (High-Dose EGCG)",
        "category": "Herbal Supplement",
        "class": "Antioxidant / Proteasome Binder",
        "cyp_enzymes": ["CYP3A4", "OATP Transporters"],
        "clearance": "Biliary",
        "toxicity_profile": ["Hepatotoxicity (at >800mg EGCG)", "Direct Proteasome Inhibitor Antagonism"],
        "description": "Concentrated EGCG directly chemically binds and inactivates bortezomib and neutralizes therapeutic ROS."
    },
    {
        "id": "ginkgo_biloba",
        "name": "Ginkgo Biloba",
        "category": "Herbal Supplement",
        "class": "PAF Inhibitor / Anticoagulant Herbal",
        "cyp_enzymes": ["CYP2C9", "CYP3A4"],
        "clearance": "Renal / Hepatic",
        "toxicity_profile": ["Spontaneous Hemorrhage", "Bleeding Diathesis"],
        "description": "Inhibits platelet-activating factor (PAF); drastically amplifies surgical and thrombocytopenic bleeding."
    },
    {
        "id": "vitamin_c_high_dose",
        "name": "High-Dose Vitamin C (>2000mg / IV)",
        "category": "Dietary Supplement",
        "class": "Antioxidant / Free Radical Scavenger",
        "cyp_enzymes": [],
        "clearance": "Renal",
        "toxicity_profile": ["Oxalate Nephropathy", "Antagonism of Radiation / Alkylating Chemotherapy"],
        "description": "Scavenges reactive oxygen species (ROS) needed by radiation and anthracyclines to trigger cancer apoptosis."
    },
    {
        "id": "vitamin_e",
        "name": "Vitamin E (>400 IU Alpha-Tocopherol)",
        "category": "Dietary Supplement",
        "class": "Lipophilic Antioxidant / Anticoagulant",
        "cyp_enzymes": ["CYP3A4 (mild)"],
        "clearance": "Biliary",
        "toxicity_profile": ["Impaired Radiotherapy Efficacy", "Bleeding Risk"],
        "description": "Antioxidant that blocks radiation-induced cell kill and increases surgical and mucosal bleeding."
    },
    {
        "id": "garlic_extract",
        "name": "Garlic Extract / Allicin (High Dose)",
        "category": "Herbal Supplement",
        "class": "Antiplatelet / CYP2E1 Inhibitor",
        "cyp_enzymes": ["CYP2E1", "CYP3A4"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Platelet Dysfunction", "Surgical Bleeding Complications"],
        "description": "Inhibits thromboxane synthase and platelet aggregation; increases risk of perioperative hemorrhage."
    },
    {
        "id": "ginger_root",
        "name": "Ginger Root (Dietary / Tea / Mild)",
        "category": "Herbal Supplement",
        "class": "5-HT3 Antagonist & Anti-Emetic",
        "cyp_enzymes": [],
        "clearance": "Hepatic",
        "toxicity_profile": ["Mild Antiplatelet at Massive Doses (>4g/day)"],
        "description": "Gentle, evidence-supported natural remedy for chemotherapy nausea; safe at moderate dietary doses."
    },
    {
        "id": "melatonin",
        "name": "Melatonin (1-5mg)",
        "category": "Dietary Supplement",
        "class": "Neurohormone / Circadian Regulator",
        "cyp_enzymes": ["CYP1A2"],
        "clearance": "Hepatic",
        "toxicity_profile": ["Mild Daytime Drowsiness"],
        "description": "Supports circadian rhythm and sleep quality; generally favorable in early to advanced supportive care."
    },
    {
        "id": "calcium_vitamin_d",
        "name": "Calcium & Vitamin D3",
        "category": "Dietary Supplement",
        "class": "Bone Health Mineral & Hormone",
        "cyp_enzymes": [],
        "clearance": "Renal",
        "toxicity_profile": ["Hypercalcemia (if over-supplemented)"],
        "description": "Standard supportive pairing during aromatase inhibitor therapy (Letrozole) to preserve bone mineral density."
    }
]


# Explicit pair-wise and class-wise interaction rules
INTERACTION_RULES: List[Dict[str, Any]] = [
    # 1. St. John's Wort + Chemotherapy / Targeted Therapies
    {
        "drug_a": "st_johns_wort",
        "drug_b": "paclitaxel",
        "severity": "CONTRAINDICATED",
        "title": "Severe Sub-Therapeutic Chemotherapy Failure",
        "mechanism": "St. John's Wort is a potent transcriptional inducer of Cytochrome P450 3A4 and P-glycoprotein efflux pumps.",
        "clinical_impact": "Accelerates clearance of paclitaxel by up to 40-50%, leading to sub-therapeutic blood concentrations and potential cancer treatment failure.",
        "recommendation": "Strictly discontinue St. John's Wort immediately. Allow a 14-day washout period before initiating or resuming taxane therapy.",
        "evidence": "FDA Black Box Oncology Guidelines & Clinical Pharmacokinetics"
    },
    {
        "drug_a": "st_johns_wort",
        "drug_b": "tamoxifen",
        "severity": "CONTRAINDICATED",
        "title": "Disruption of Endoxifen Bioactivation & Accelerated Tamoxifen Clearance",
        "mechanism": "Induction of multiple hepatic enzymes alters the precise metabolic ratio required to convert tamoxifen to its active metabolite Endoxifen.",
        "clinical_impact": "Loss of estrogen receptor suppression, significantly raising the risk of breast cancer recurrence or metastatic relapse.",
        "recommendation": "Avoid completely. For mood or hot flashes, consult oncology for vetted alternatives such as Venlafaxine or Gabapentin.",
        "evidence": "Clinical Breast Cancer Pharmacogenetics Consensus"
    },
    {
        "drug_a": "st_johns_wort",
        "drug_b": "osimertinib",
        "severity": "CONTRAINDICATED",
        "title": "Catastrophic Decrease in Targeted TKI Exposure",
        "mechanism": "St. John's Wort dramatically increases CYP3A4-mediated hepatic oxidation of Osimertinib.",
        "clinical_impact": "Reduces Osimertinib AUC (systemic exposure) by ~75%, allowing EGFR-mutated lung cancer cells to escape drug pressure.",
        "recommendation": "Contraindicated. Do not administer together under any circumstances.",
        "evidence": "FDA Prescribing Information (Tagrisso) & NCCN Guidelines"
    },
    {
        "drug_a": "st_johns_wort",
        "drug_b": "dexamethasone",
        "severity": "MAJOR",
        "title": "Accelerated Steroid Metabolism",
        "mechanism": "CYP3A4 induction speeds elimination of dexamethasone.",
        "clinical_impact": "Loss of control over brain edema or chemotherapy-induced emesis.",
        "recommendation": "Discontinue St. John's Wort; monitor patient for increased nausea or intracranial pressure symptoms.",
        "evidence": "Pharmacological Drug Interaction Database"
    },

    # 2. High-Dose Antioxidants + ROS-Dependent Chemotherapy / Radiation
    {
        "drug_a": "vitamin_c_high_dose",
        "drug_b": "doxorubicin",
        "severity": "CONTRAINDICATED",
        "title": "Direct Antagonism of Anthracycline-Induced Apoptosis",
        "mechanism": "Doxorubicin relies on generating intracellular reactive oxygen species (ROS) and DNA breaks to kill cancer cells.",
        "clinical_impact": "High-dose Vitamin C scavenges free radicals directly inside tumor cells, physically protecting malignant cells from chemotherapy-induced cell death.",
        "recommendation": "Avoid high-dose antioxidant infusions (>1000mg/day) during active doxorubicin therapy cycles. Dietary fruit intake remains safe.",
        "evidence": "Journal of Clinical Oncology & Memorial Sloan Kettering Integrative Medicine"
    },
    {
        "drug_a": "vitamin_c_high_dose",
        "drug_b": "cisplatin",
        "severity": "MAJOR",
        "title": "Antioxidant Interference with Platinum DNA Adduct Formation",
        "mechanism": "Supraphysiologic Vitamin C neutralizes oxidative stress necessary for platinum-induced crosslink cytotoxicity.",
        "clinical_impact": "Reduces cytotoxic tumor cell death and may contribute to tubular oxalate crystalluria in kidneys already stressed by cisplatin.",
        "recommendation": "Do not consume megadose oral or IV Vitamin C during platinum therapy days. Restrict to dietary food sources.",
        "evidence": "Oncology Pharmacotherapy Reviews"
    },
    {
        "drug_a": "vitamin_e",
        "drug_b": "doxorubicin",
        "severity": "MAJOR",
        "title": "Antioxidant Blunting of Cytotoxic Antitumor Efficacy",
        "mechanism": "Alpha-tocopherol inserts into lipid membranes and intercepts peroxyl radicals needed for anthracycline antitumor activity.",
        "clinical_impact": "Decreases cancer cell apoptotic response; may also potentiate bleeding complications if platelets are depressed.",
        "recommendation": "Stop high-dose Vitamin E (>400 IU) during chemotherapy and radiation treatments.",
        "evidence": "ASCO / Society for Integrative Oncology Clinical Guidelines"
    },

    # 3. High-Dose Green Tea Extract + Bortezomib / Chemotherapy
    {
        "drug_a": "green_tea_extract",
        "drug_b": "doxorubicin",
        "severity": "MAJOR",
        "title": "P-glycoprotein & Transporter Interference",
        "mechanism": "High concentrations of epigallocatechin-3-gallate (EGCG) inhibit OATP and P-gp, altering anthracycline distribution and clearance.",
        "clinical_impact": "Unpredictable systemic toxicity and risk of hepatotoxicity when high-dose EGCG (>800mg) is taken with hepatically cleared chemotherapy.",
        "recommendation": "Limit green tea to 1-2 freshly brewed cups daily; avoid concentrated weight-loss or antioxidant green tea pills.",
        "evidence": "European Journal of Cancer & Clinical Pharmacology"
    },

    # 4. Anticoagulants & Antiplatelets (Ginkgo, Garlic, Curcumin, NSAIDs)
    {
        "drug_a": "ginkgo_biloba",
        "drug_b": "warfarin",
        "severity": "CONTRAINDICATED",
        "title": "Severe Synergistic Spontaneous Bleeding Risk",
        "mechanism": "Ginkgolides inhibit platelet-activating factor (PAF) while warfarin depletes Vitamin K clotting factors II, VII, IX, and X.",
        "clinical_impact": "Dramatically prolonged bleeding time, severe internal hemorrhage, subdural hematoma, or gastrointestinal bleeding.",
        "recommendation": "Strictly contraindicated. Cease Ginkgo Biloba immediately.",
        "evidence": "American College of Chest Physicians (CHEST) Antithrombotic Guidelines"
    },
    {
        "drug_a": "ginkgo_biloba",
        "drug_b": "ibuprofen",
        "severity": "MAJOR",
        "title": "Additive Gastric & Platelet Hemorrhagic Vulnerability",
        "mechanism": "Dual suppression of cyclooxygenase-1 and PAF impairs both platelet plug formation and gastric mucosal cytoprotection.",
        "clinical_impact": "Elevated incidence of upper gastrointestinal ulceration and microvascular bleeding, exacerbated during chemotherapy thrombocytopenia.",
        "recommendation": "Discontinue Ginkgo. Prefer acetaminophen for mild analgesia under clinical monitoring.",
        "evidence": "Pharmacotherapy Drug Safety Reports"
    },
    {
        "drug_a": "garlic_extract",
        "drug_b": "warfarin",
        "severity": "MAJOR",
        "title": "Antiplatelet Augmentation of Anticoagulant Effect",
        "mechanism": "Allicin metabolites irreversibly inhibit platelet aggregation and may weakly alter CYP2C9 metabolism.",
        "clinical_impact": "Unpredictable spikes in INR and prolonged bleeding times.",
        "recommendation": "Avoid high-dose garlic supplement capsules. Culinary garlic used as standard cooking seasoning is permissible.",
        "evidence": "Integrative Medicine Oncology Guidelines"
    },
    {
        "drug_a": "curcumin",
        "drug_b": "warfarin",
        "severity": "MODERATE",
        "title": "Mild Antiplatelet Synergy & Mild CYP2C9 Competition",
        "mechanism": "High-dose curcumin exhibits mild antithrombotic properties and competitive inhibition of CYP2C9.",
        "clinical_impact": "May slightly increase INR and bruising in anticoagulated patients.",
        "recommendation": "Monitor INR closely if patient consumes concentrated curcumin extracts (>1000mg/day). Culinary turmeric in food is safe.",
        "evidence": "Journal of Clinical Pharmacy and Therapeutics"
    },
    {
        "drug_a": "curcumin",
        "drug_b": "tamoxifen",
        "severity": "MODERATE",
        "title": "Potential Mild CYP2D6 / CYP3A4 In-Vitro Interference",
        "mechanism": "Concentrated curcumin extract may weakly inhibit CYP2D6 in vitro, the enzyme required for tamoxifen bioactivation.",
        "clinical_impact": "Theoretical risk of lowering Endoxifen levels if consumed in massive supplemental doses (>2000mg/day with piperine).",
        "recommendation": "Avoid high-dose bioavailability-enhanced curcumin supplements while on tamoxifen. Dietary spice use is unrestricted.",
        "evidence": "In Vitro & Pharmacokinetic Oncology Reports"
    },

    # 5. NSAIDs + Methotrexate / Cisplatin
    {
        "drug_a": "ibuprofen",
        "drug_b": "methotrexate",
        "severity": "CONTRAINDICATED",
        "title": "Severe Renal Clearance Blockade & Lethal Methotrexate Toxicity",
        "mechanism": "NSAIDs competitively inhibit organic anion transporters (OAT1/OAT3) in the proximal renal tubules and reduce renal blood flow.",
        "clinical_impact": "Dramatically reduces methotrexate excretion, causing life-threatening pancytopenia, acute kidney injury, and denuding mucositis.",
        "recommendation": "Strictly contraindicated with intermediate and high-dose methotrexate. Use non-NSAID alternatives (e.g. acetaminophen, local ice) under oncology guidance.",
        "evidence": "FDA Black Box Warning (Methotrexate) & Hematology Guidelines"
    },
    {
        "drug_a": "ibuprofen",
        "drug_b": "cisplatin",
        "severity": "MAJOR",
        "title": "Additive Nephrotoxicity & Prerenal Azotemia",
        "mechanism": "Cisplatin induces tubular necrosis while NSAIDs constrict afferent renal arterioles by blocking protective prostaglandins.",
        "clinical_impact": "Accelerates acute kidney injury (AKI) and may cause permanent loss of renal filtration function.",
        "recommendation": "Avoid NSAIDs during platinum therapy weeks. Maintain vigorous IV hydration and electrolyte monitoring.",
        "evidence": "American Journal of Kidney Diseases"
    },

    # 6. PPIs (Omeprazole) + Kinase Inhibitors (Osimertinib, Erlotinib, etc.)
    {
        "drug_a": "omeprazole",
        "drug_b": "osimertinib",
        "severity": "MODERATE",
        "title": "Gastric pH Dependent Bioavailability Interaction",
        "mechanism": "Proton pump inhibitors elevate intragastric pH (>4.0), which can alter dissolution and absorption of weakly basic kinase inhibitors.",
        "clinical_impact": "May slightly decrease peak plasma levels (Cmax) of oral TKIs, although Osimertinib is less pH-sensitive than earlier generation TKIs (Erlotinib/Gefitinib).",
        "recommendation": "If acid suppression is required, consider spacing H2-blockers or antacids 2 hours before or 4 hours after TKI administration.",
        "evidence": "Clinical Pharmacokinetics of Oral Targeted Kinase Inhibitors"
    },
    {
        "drug_a": "ginkgo_biloba",
        "drug_b": "temozolomide",
        "severity": "CONTRAINDICATED",
        "title": "Severe Intracranial Hemorrhage Risk in Malignant Brain Neoplasms",
        "mechanism": "Temozolomide causes myelosuppression and cumulative thrombocytopenia (low platelets), while Ginkgolides potently antagonize Platelet-Activating Factor (PAF).",
        "clinical_impact": "Massively elevates risk of life-threatening intratumoral bleeding, acute subdural hematoma, and catastrophic hemorrhagic stroke within cranial lesions.",
        "recommendation": "Strictly contraindicated in all brain tumor and neuro-oncology regimens. Cease Ginkgo Biloba immediately.",
        "evidence": "Neuro-Oncology Clinical Practice Guidelines & Mayo Clinic Integrative Medicine"
    },
    {
        "drug_a": "st_johns_wort",
        "drug_b": "dexamethasone",
        "severity": "MAJOR",
        "title": "Accelerated Corticosteroid Clearance & Loss of Cerebral Edema Control",
        "mechanism": "St. John's Wort strongly induces hepatic CYP3A4, the primary enzyme responsible for systemic dexamethasone elimination.",
        "clinical_impact": "Dramatically lowers dexamethasone half-life and circulating levels, precipitating rapid rebound vasogenic cerebral edema or acute emetic failure.",
        "recommendation": "Discontinue St. John's Wort immediately. Maintain stable dexamethasone titration.",
        "evidence": "Clinical Pharmacology & Therapeutics"
    },
    {
        "drug_a": "vitamin_c_high_dose",
        "drug_b": "carboplatin",
        "severity": "CONTRAINDICATED",
        "title": "Direct Antagonism of Platinum-Induced Tumor Cell Apoptosis",
        "mechanism": "Carboplatin relies on generating reactive oxygen species (ROS) and DNA intrastrand crosslinks. Megadose antioxidant Vitamin C neutralizes free radicals inside malignant cells.",
        "clinical_impact": "Significantly attenuates chemotherapy-induced cytotoxicity, protecting malignant tumor cells from programmed death.",
        "recommendation": "Avoid high-dose antioxidant infusions and megadose Vitamin C (>1000mg/day) during active chemotherapy cycles.",
        "evidence": "Memorial Sloan Kettering Integrative Medicine & Journal of Clinical Oncology"
    },

    # 7. Beneficial Supportive Pairings (Safe / Synergistic)
    {
        "drug_a": "ginger_root",
        "drug_b": "ondansetron",
        "severity": "BENEFICIAL",
        "title": "Safe & Synergistic Anti-Emetic Support",
        "mechanism": "Ginger compounds (gingerols and shogaols) act locally in the gastrointestinal tract and on peripheral 5-HT3 receptors without competing for hepatic CYP metabolism.",
        "clinical_impact": "Clinically proven to reduce delayed and anticipatory nausea by 20-30% when combined with standard 5-HT3 antagonist regimens.",
        "recommendation": "Safe and recommended: sip fresh ginger tea or take mild standardized ginger root (500-1000mg/day) 30 minutes before meals.",
        "evidence": "National Cancer Institute (NCI) Community Oncology Research Trial"
    },
    {
        "drug_a": "calcium_vitamin_d",
        "drug_b": "letrozole",
        "severity": "BENEFICIAL",
        "title": "Standard Clinical Bone Preservation Regimen",
        "mechanism": "Aromatase inhibitors exhaust systemic estrogen, accelerating osteoclast bone resorption. Calcium + Vitamin D3 support osteoblast remineralization.",
        "clinical_impact": "Protects against AI-induced bone mineral density (BMD) loss and reduces risk of pathological fragility fractures.",
        "recommendation": "Standard of care: 1000-1200mg Calcium daily (diet + supplement) and 800-2000 IU Vitamin D3, with baseline DEXA scans.",
        "evidence": "ASCO / ESMO Clinical Practice Guidelines for Bone Health in Breast Cancer"
    },
    {
        "drug_a": "melatonin",
        "drug_b": "temozolomide",
        "severity": "BENEFICIAL",
        "title": "Favorable Sleep Architecture & Potential Radiosensitization",
        "mechanism": "Melatonin does not interfere with temozolomide's chemical hydrolysis; exhibits mild neuroprotective and sleep-stabilizing properties.",
        "clinical_impact": "Improves nocturnal restorative sleep during intensive neuro-oncology treatment cycles without compromising chemotherapy.",
        "recommendation": "Safe at 1-5mg at bedtime. Inform radiation oncologist.",
        "evidence": "Integrative Neuro-Oncology Clinical Reviews"
    }
]


def get_drug_database(search_query: str = "", category: str = "") -> List[Dict[str, Any]]:
    """Return filtered drugs/supplements based on search text and category."""
    q = (search_query or "").strip().lower()
    cat = (category or "").strip().lower()
    results = []

    for drug in DRUG_DATABASE:
        if cat and cat != "all":
            if cat not in drug["category"].lower() and cat not in drug.get("class", "").lower():
                continue
        if q:
            match = (
                q in drug["name"].lower()
                or q in drug["id"].lower()
                or q in drug["category"].lower()
                or q in drug.get("class", "").lower()
                or q in drug.get("description", "").lower()
            )
            if not match:
                continue
        results.append(drug)

    return results


def check_interactions(selected_item_ids: List[str]) -> Dict[str, Any]:
    """
    Analyzes an array of selected drug and supplement IDs.
    Returns detected interactions, severity levels, overall safety score,
    CYP450 enzyme conflicts, organ toxicity flags, and actionable recommendations.
    """
    normalized_ids = [str(x).strip().lower() for x in selected_item_ids if x]
    # Remove duplicates
    unique_ids = list(dict.fromkeys(normalized_ids))

    # Resolve items
    resolved_items = []
    item_map = {d["id"]: d for d in DRUG_DATABASE}
    for iid in unique_ids:
        if iid in item_map:
            resolved_items.append(item_map[iid])

    detected_interactions: List[Dict[str, Any]] = []
    beneficial_pairings: List[Dict[str, Any]] = []

    # Check pair-wise combinations
    n = len(unique_ids)
    for i in range(n):
        for j in range(i + 1, n):
            id_a = unique_ids[i]
            id_b = unique_ids[j]

            # Search in rules
            for rule in INTERACTION_RULES:
                matches_direct = (rule["drug_a"] == id_a and rule["drug_b"] == id_b)
                matches_reverse = (rule["drug_a"] == id_b and rule["drug_b"] == id_a)

                if matches_direct or matches_reverse:
                    entry = {
                        "drug_a": item_map.get(rule["drug_a"], {"name": rule["drug_a"]})["name"],
                        "drug_b": item_map.get(rule["drug_b"], {"name": rule["drug_b"]})["name"],
                        "drug_a_id": rule["drug_a"],
                        "drug_b_id": rule["drug_b"],
                        "severity": rule["severity"],
                        "title": rule["title"],
                        "mechanism": rule["mechanism"],
                        "clinical_impact": rule["clinical_impact"],
                        "recommendation": rule["recommendation"],
                        "evidence": rule.get("evidence", "Oncology Clinical Practice")
                    }
                    if rule["severity"] == "BENEFICIAL":
                        beneficial_pairings.append(entry)
                    else:
                        detected_interactions.append(entry)

    # Sort interactions by severity: CONTRAINDICATED -> MAJOR -> MODERATE
    severity_order = {"CONTRAINDICATED": 0, "MAJOR": 1, "MODERATE": 2, "BENEFICIAL": 3}
    detected_interactions.sort(key=lambda x: severity_order.get(x["severity"], 99))

    # Calculate overall Safety Score (0-100)
    contraindicated_count = sum(1 for x in detected_interactions if x["severity"] == "CONTRAINDICATED")
    major_count = sum(1 for x in detected_interactions if x["severity"] == "MAJOR")
    moderate_count = sum(1 for x in detected_interactions if x["severity"] == "MODERATE")
    beneficial_count = len(beneficial_pairings)

    if contraindicated_count > 0:
        safety_score = max(15, 40 - (contraindicated_count * 10) - (major_count * 5))
        safety_status = "CRITICAL HAZARD — CONTRAINDICATION DETECTED"
        safety_badge_class = "danger"
    elif major_count > 0:
        safety_score = max(45, 68 - (major_count * 8) - (moderate_count * 3))
        safety_status = "HIGH RISK — SIGNIFICANT CLINICAL CONFLICT"
        safety_badge_class = "warning"
    elif moderate_count > 0:
        safety_score = max(72, 85 - (moderate_count * 4))
        safety_status = "MODERATE CAUTION — MONITORING ADVISED"
        safety_badge_class = "warning"
    else:
        safety_score = min(100, 95 + (2 if beneficial_count > 0 else 0))
        safety_status = "OPTIMAL SAFETY — NO ADVERSE CONFLICTS FOUND"
        safety_badge_class = "success"

    # Identify CYP Enzymes and Organ Toxicities involved across all items
    cyp_enzymes = set()
    organ_toxicities = set()
    for item in resolved_items:
        for c in item.get("cyp_enzymes", []):
            cyp_enzymes.add(c)
        for t in item.get("toxicity_profile", []):
            organ_toxicities.add(t)

    # Summary note
    if contraindicated_count > 0:
        summary_text = (
            f"ALERT: Detected {contraindicated_count} contraindicated combination(s). "
            f"Taking these supplements alongside your cancer treatment may physically counteract "
            f"anticancer efficacy or precipitate severe medical toxicity. Discuss immediately with your oncologist."
        )
    elif major_count > 0:
        summary_text = (
            f"CAUTION: Identified {major_count} major drug/supplement conflict(s). "
            f"Dose separation, drug adjustment, or temporary supplement suspension is strongly recommended."
        )
    elif moderate_count > 0:
        summary_text = (
            f"MONITOR: Found {moderate_count} moderate interaction(s). "
            f"Maintain hydration and report any unusual digestive or bleeding symptoms to your clinical team."
        )
    elif len(resolved_items) == 0:
        summary_text = "Please select at least two oncology medications or supplements to analyze interaction pathways."
    else:
        summary_text = (
            f"All {len(resolved_items)} selected medications and supportive supplements appear compatible "
            f"with no known adverse pharmacokinetic or pharmacodynamic interactions detected."
        )

    return {
        "analyzed_count": len(resolved_items),
        "items": resolved_items,
        "safety_score": safety_score,
        "safety_status": safety_status,
        "safety_badge_class": safety_badge_class,
        "counts": {
            "contraindicated": contraindicated_count,
            "major": major_count,
            "moderate": moderate_count,
            "beneficial": beneficial_count
        },
        "interactions": detected_interactions,
        "beneficial_pairings": beneficial_pairings,
        "cyp_enzymes": sorted(list(cyp_enzymes)),
        "organ_toxicities": sorted(list(organ_toxicities)),
        "summary": summary_text,
        "disclaimer": (
            "Clinical Disclaimer: This Oncology Medication & Supplement Interaction Checker is an evidence-based "
            "decision-support resource. It is not an automated medical prescription and does not replace individualized "
            "pharmacotherapy consultation with a board-certified oncologist or oncology clinical pharmacist."
        )
    }


# ===========================================================================
# STAGE-SPECIFIC ONCOLOGY PRESCRIPTIONS DATABASE
# ===========================================================================

def normalize_stage_code(stage_str: str) -> str:
    s = (stage_str or "").strip().lower()
    if "iv" in s or "4" in s:
        return "Stage IV"
    if "iii" in s or "3" in s:
        return "Stage III"
    if "ii" in s or "2" in s:
        return "Stage II"
    if "i" in s or "1" in s:
        return "Stage I"
    return "Stage 0"


ONCOLOGY_STAGE_PRESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    # ------------------ BREAST CANCER ------------------
    "breast_stage_0": {
        "cancer_type": "breast",
        "cancer_name": "Breast Cancer",
        "stage": "Stage 0",
        "stage_label": "Carcinoma In-Situ (DCIS / LCIS)",
        "protocol_name": "Endocrine Chemoprevention & Surveillance Protocol",
        "clinical_intent": "Adjuvant Risk Reduction & Prevention of Invasive Progression",
        "evidence_guideline": "NCCN Breast Cancer Guidelines (v2.2024) & NSABP B-24 Protocol",
        "prescribed_core_drugs": [
            {
                "id": "tamoxifen",
                "name": "Tamoxifen Citrate",
                "category": "Endocrine Therapy",
                "class": "Selective Estrogen Receptor Modulator (SERM)",
                "dosage": "20 mg PO daily for 5 years",
                "role": "Competitively blocks estrogen receptors in mammary tissue, reducing contralateral and local invasive recurrence by >45%."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "calcium_vitamin_d",
                "name": "Calcium & Vitamin D3",
                "category": "Dietary Supplement",
                "class": "Bone Health Mineral & Hormone",
                "dosage": "1000 mg Calcium + 800 IU Vit D3 PO daily",
                "role": "Preserves bone mineral density and counteracts osteopenia."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO at bedtime",
                "role": "Supports circadian rhythm and quality of sleep during endocrine therapy."
            }
        ],
        "all_item_ids": ["tamoxifen", "calcium_vitamin_d", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort (Hypericum perforatum)",
                "hazard": "Potent CYP3A4 & P-gp induction drastically reduces metabolic activation of Tamoxifen into active endoxifen, causing chemoprevention failure."
            },
            {
                "name": "High-Dose Curcumin Extracts",
                "hazard": "Weak CYP2D6/CYP3A4 inhibition competes with tamoxifen bioactivation."
            }
        ],
        "safe_remedies_and_habits": [
            "Maintain 150+ minutes of weekly aerobic exercise (brisk walking, swimming)",
            "Adopt an anti-inflammatory Mediterranean dietary pattern with cruciferous vegetables",
            "Annual diagnostic mammography and bilateral breast MRI surveillance"
        ]
    },
    "breast_stage_i": {
        "cancer_type": "breast",
        "cancer_name": "Breast Cancer",
        "stage": "Stage I",
        "stage_label": "Early Invasive Breast Malignancy (T1N0M0)",
        "protocol_name": "Post-Lumpectomy Adjuvant Endocrine & Anti-HER2 Regimen",
        "clinical_intent": "Adjuvant Curative Systemic Prophylaxis",
        "evidence_guideline": "ASCO / NCCN Clinical Practice Guidelines in Early Breast Cancer",
        "prescribed_core_drugs": [
            {
                "id": "tamoxifen",
                "name": "Tamoxifen Citrate (or Letrozole if postmenopausal)",
                "category": "Endocrine Therapy",
                "class": "SERM / Aromatase Inhibitor",
                "dosage": "20 mg PO daily (or Letrozole 2.5 mg PO daily)",
                "role": "Suppresses estrogen-driven proliferation in hormone-receptor positive disease."
            },
            {
                "id": "trastuzumab",
                "name": "Trastuzumab (Herceptin)",
                "category": "Targeted Therapy",
                "class": "HER2 Receptor Monoclonal Antibody",
                "dosage": "8 mg/kg loading, then 6 mg/kg IV Q3W x 1 year (if HER2+)",
                "role": "Directly targets extracellular domain of HER2 tyrosine kinase receptor."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Receptor Antagonist",
                "dosage": "8 mg PO PRN for infusion nausea",
                "role": "Prevents and manages mild infusion-related or oral emesis."
            },
            {
                "id": "calcium_vitamin_d",
                "name": "Calcium & Vitamin D3",
                "category": "Dietary Supplement",
                "class": "Bone Health Mineral & Hormone",
                "dosage": "1200 mg / 1000 IU daily",
                "role": "Maintains cortical bone density during hormonal suppression."
            }
        ],
        "all_item_ids": ["tamoxifen", "trastuzumab", "ondansetron", "calcium_vitamin_d"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates tamoxifen clearance and abolishes therapeutic endoxifen levels."
            },
            {
                "name": "Ginkgo Biloba & High-Dose Garlic",
                "hazard": "Platelet-activating factor (PAF) inhibition increases bleeding diathesis during biopsy/surveillance."
            }
        ],
        "safe_remedies_and_habits": [
            "Regular cardiovascular telemetry (echocardiogram) every 3 months for LVEF monitoring on Trastuzumab",
            "Gentle ginger root tea for morning digestive comfort",
            "Weight-bearing resistance exercises 2-3 times weekly"
        ]
    },
    "breast_stage_ii": {
        "cancer_type": "breast",
        "cancer_name": "Breast Cancer",
        "stage": "Stage II",
        "stage_label": "Invasive Axillary-Node Positive or T2/T3 Disease",
        "protocol_name": "Dose-Dense AC-T Adjuvant Protocol (Adriamycin + Cyclophosphamide -> Taxol)",
        "clinical_intent": "Definitive Curative Systemic Eradication of Micrometastases",
        "evidence_guideline": "CALGB 9741 & NCCN Category 1 Preferred Adjuvant Regimen",
        "prescribed_core_drugs": [
            {
                "id": "doxorubicin",
                "name": "Doxorubicin (Adriamycin)",
                "category": "Chemotherapy",
                "class": "Anthracycline Topoisomerase II Inhibitor",
                "dosage": "60 mg/m² IV every 2 weeks x 4 cycles with G-CSF support",
                "role": "Backbone cytotoxic anthracycline inducing DNA cross-links and ROS-mediated apoptosis."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (Taxol)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "175 mg/m² IV Q2W x 4 cycles (or 80 mg/m² weekly x 12)",
                "role": "Inhibits microtubule depolymerization, halting mitotic division."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "16 mg IV 30 min pre-infusion, then 8 mg PO Q12H PRN",
                "role": "Prevents highly emetogenic anthracycline-induced nausea."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "10-20 mg IV pre-medication for paclitaxel and emesis control",
                "role": "Prevents taxane hypersensitivity infusion reactions and acute emesis."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20 mg PO daily",
                "role": "Gastric mucosal protection during corticosteroid therapy."
            }
        ],
        "all_item_ids": ["doxorubicin", "paclitaxel", "ondansetron", "dexamethasone", "omeprazole"],
        "contraindicated_supplements": [
            {
                "name": "High-Dose Vitamin C (>2000mg/day) & Vitamin E",
                "hazard": "Direct ROS Apoptosis Antagonism: Doxorubicin relies on generating intracellular free radicals; antioxidants neutralize this therapeutic mechanism, protecting malignant cells."
            },
            {
                "name": "St. John's Wort",
                "hazard": "CYP3A4 induction lowers paclitaxel and doxorubicin AUC by >40%, precipitating regimen failure."
            }
        ],
        "safe_remedies_and_habits": [
            "Use scalp hypothermia (cold caps) during paclitaxel infusions to prevent alopecia",
            "Wear loose footwear and use cryotherapy mittens to reduce peripheral neuropathy",
            "Consume fresh ginger tea for breakthrough nausea between chemotherapy cycles"
        ]
    },
    "breast_stage_iii": {
        "cancer_type": "breast",
        "cancer_name": "Breast Cancer",
        "stage": "Stage III",
        "stage_label": "Locally Advanced / Inflammatory / Multi-Nodal Breast Cancer",
        "protocol_name": "Neoadjuvant Dose-Dense AC-T + Dual HER2/Hormone Targeted Protocol",
        "clinical_intent": "Neoadjuvant Downstaging & Systemic Eradication Prior to Mastectomy",
        "evidence_guideline": "NCCN Breast Cancer Guidelines (v2.2024) Category 1 Neoadjuvant",
        "prescribed_core_drugs": [
            {
                "id": "doxorubicin",
                "name": "Doxorubicin (Adriamycin)",
                "category": "Chemotherapy",
                "class": "Anthracycline Topoisomerase II Inhibitor",
                "dosage": "60 mg/m² IV Q2W x 4 cycles",
                "role": "Maximum cytoreductive potency for locally extensive primary tumor burden."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (Taxol)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "80 mg/m² IV weekly x 12 cycles",
                "role": "Eliminates lymph node micro-metastases and primary tumor bed."
            },
            {
                "id": "trastuzumab",
                "name": "Trastuzumab (Herceptin)",
                "category": "Targeted Therapy",
                "class": "HER2 Targeted Monoclonal Antibody",
                "dosage": "6 mg/kg IV Q3W (if HER2 overexpression present)",
                "role": "Inhibits downstream PI3K/Akt oncogenic survival pathways."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "16 mg IV pre-infusion + 8 mg PO Q12H x 3 days",
                "role": "High-potency emesis prevention."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "12-20 mg IV pre-chemo",
                "role": "Anti-hypersensitivity and synergistic antiemetic."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20 mg PO daily",
                "role": "Gastric mucosa protection."
            },
            {
                "id": "calcium_vitamin_d",
                "name": "Calcium & Vitamin D3",
                "category": "Dietary Supplement",
                "class": "Bone Health Mineral & Hormone",
                "dosage": "1000 mg / 800 IU daily",
                "role": "Bone density stabilization."
            }
        ],
        "all_item_ids": ["doxorubicin", "paclitaxel", "trastuzumab", "ondansetron", "dexamethasone", "omeprazole"],
        "contraindicated_supplements": [
            {
                "name": "High-Dose Vitamin C & E Megadoses",
                "hazard": "Scavenges intracellular free radicals required by Doxorubicin to destroy cancer cell DNA."
            },
            {
                "name": "Green Tea Extract (High-Dose EGCG >800mg)",
                "hazard": "Hepatotoxicity synergy with paclitaxel; direct antagonism of therapeutic oxidative stress."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Severe CYP3A4/P-gp clearance leads to sub-therapeutic cytotoxic drug exposure."
            }
        ],
        "safe_remedies_and_habits": [
            "Strict oral hygiene with non-alcoholic baking soda rinses to prevent mucositis",
            "High-protein nutrition (>1.5 g/kg/day) to maintain absolute neutrophil count (ANC)",
            "Frequent low-impact walking and targeted lymphatic drainage exercises"
        ]
    },
    "breast_stage_iv": {
        "cancer_type": "breast",
        "cancer_name": "Breast Cancer",
        "stage": "Stage IV",
        "stage_label": "Metastatic / Advanced Breast Carcinoma",
        "protocol_name": "Systemic Targeted Chemo-Immunotherapy & Endocrine Maintenance",
        "clinical_intent": "Prolongation of Progression-Free Survival & Quality-of-Life Palliative Optimization",
        "evidence_guideline": "NCCN Metastatic Breast Cancer Guidelines (v2.2024)",
        "prescribed_core_drugs": [
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (or Docetaxel)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "80 mg/m² IV weekly (Days 1, 8, 15 of 28-day cycle)",
                "role": "Sustains cytotoxic mitotic blockade with manageable bone marrow toxicity."
            },
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda)",
                "category": "Immunotherapy",
                "class": "PD-1 Immune Checkpoint Inhibitor",
                "dosage": "200 mg IV Q3W (if PD-L1 CPS ≥10 in triple-negative)",
                "role": "Unleashes T-cell cytotoxic response against distant metastatic tumor cells."
            },
            {
                "id": "letrozole",
                "name": "Letrozole (Femara)",
                "category": "Targeted Therapy",
                "class": "Non-Steroidal Aromatase Inhibitor",
                "dosage": "2.5 mg PO daily (if HR+)",
                "role": "Blocks peripheral estrogen synthesis in postmenopausal metastatic disease."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO Q8H PRN",
                "role": "Antiemetic symptom control."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "8 mg PO prior to taxane",
                "role": "Taxane pre-medication and appetite stimulation."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO at bedtime",
                "role": "Supports circadian rhythm, sleep architecture, and reduces fatigue."
            },
            {
                "id": "calcium_vitamin_d",
                "name": "Calcium & Vitamin D3",
                "category": "Dietary Supplement",
                "class": "Bone Health Mineral & Hormone",
                "dosage": "1200 mg / 1000 IU daily",
                "role": "Protects against skeletal-related events (SREs) in bone metastases."
            }
        ],
        "all_item_ids": ["paclitaxel", "pembrolizumab", "letrozole", "ondansetron", "melatonin", "calcium_vitamin_d"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates clearance of paclitaxel and targeted agents, risking sudden tumor progression."
            },
            {
                "name": "Ginkgo Biloba & High-Dose Garlic",
                "hazard": "Increases spontaneous bleeding hazard in patients with thrombocytopenia or anticoagulation."
            }
        ],
        "safe_remedies_and_habits": [
            "Palliative psycho-oncology support and mindfulness meditation for symptom relief",
            "Gentle passive range-of-motion stretching and fall prevention measures",
            "Nutritional meal replacements rich in healthy fats (avocado, olive oil, walnuts)"
        ]
    },

    # ------------------ LUNG CANCER ------------------
    "lung_stage_0": {
        "cancer_type": "lung",
        "cancer_name": "Lung Cancer",
        "stage": "Stage 0",
        "stage_label": "Carcinoma In-Situ / Atypical Adenomatous Hyperplasia",
        "protocol_name": "Pulmonary Chemoprevention & High-Resolution LDCT Surveillance",
        "clinical_intent": "Carcinogen Clearance, Mucosal Repair & Secondary Prevention",
        "evidence_guideline": "USPSTF & American Thoracic Society (ATS) Guidelines",
        "prescribed_core_drugs": [],
        "prescribed_supportive_drugs": [
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone / Antioxidant",
                "dosage": "3 mg PO nightly",
                "role": "Supports alveolar epithelial DNA repair mechanisms during nocturnal sleep."
            },
            {
                "id": "ginger_root",
                "name": "Ginger Root Infusion",
                "category": "Herbal Supplement",
                "class": "Natural Anti-Inflammatory",
                "dosage": "Fresh tea 1-2 cups daily",
                "role": "Soothes chronic bronchial irritation and reduces airway oxidative markers."
            }
        ],
        "all_item_ids": ["melatonin", "ginger_root"],
        "contraindicated_supplements": [
            {
                "name": "High-Dose Synthetic Beta-Carotene",
                "hazard": "Paradoxically increases lung carcinogenesis risk in current and former tobacco smokers (CARET study)."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Metabolic CYP3A4 perturbation without clinical indication."
            }
        ],
        "safe_remedies_and_habits": [
            "Complete tobacco smoke and occupational aerosol cessation program",
            "Annual Low-Dose Computed Tomography (LDCT) screening without contrast",
            "Diaphragmatic pulmonary expansion breathing exercises 15 minutes twice daily"
        ]
    },
    "lung_stage_i": {
        "cancer_type": "lung",
        "cancer_name": "Lung Cancer",
        "stage": "Stage I",
        "stage_label": "Early-Stage Non-Small Cell Lung Cancer (T1N0M0)",
        "protocol_name": "Post-Resection Adjuvant Targeted Surveillance / Osimertinib Protocol",
        "clinical_intent": "Curative Adjuvant Disease-Free Survival Prolongation",
        "evidence_guideline": "ADAURA Clinical Trial & NCCN Category 1 for EGFR Exon 19/21+",
        "prescribed_core_drugs": [
            {
                "id": "osimertinib",
                "name": "Osimertinib (Tagrisso)",
                "category": "Targeted Therapy",
                "class": "3rd-Generation EGFR Tyrosine Kinase Inhibitor",
                "dosage": "80 mg PO once daily (if EGFR positive)",
                "role": "Selectively inhibits EGFR sensitizing and T790M resistance mutations, preventing central nervous system and distant relapse."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO PRN for mild nausea",
                "role": "Manages initial oral TKI GI sensitivity."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO nightly",
                "role": "Circadian rest and neuro-protection."
            }
        ],
        "all_item_ids": ["osimertinib", "ondansetron", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Potent CYP3A4 inducer: Drops systemic osimertinib plasma concentrations by >75%, completely nullifying targeted tumor control."
            },
            {
                "name": "High-Dose Proton Pump Inhibitors (Concurrent Hour)",
                "hazard": "Alters gastric pH and significantly suppresses intestinal absorption of oral kinase inhibitors."
            }
        ],
        "safe_remedies_and_habits": [
            "Inspiratory muscle spirometry training post-thoracotomy/VATS resection",
            "Monitor for dry skin / paronychia and use fragrance-free ceramide ointments",
            "Surveillance chest CT every 6 months for the first 2 years"
        ]
    },
    "lung_stage_ii": {
        "cancer_type": "lung",
        "cancer_name": "Lung Cancer",
        "stage": "Stage II",
        "stage_label": "Resected NSCLC with Bronchial / Hilar Lymph Node Involvement",
        "protocol_name": "Adjuvant Cisplatin/Carboplatin + Paclitaxel Doublet Chemotherapy",
        "clinical_intent": "Adjuvant Eradication of Occult Nodal Micrometastases",
        "evidence_guideline": "ANITA / IALT Trials & NCCN Standard Adjuvant Platinum Doublet",
        "prescribed_core_drugs": [
            {
                "id": "cisplatin",
                "name": "Cisplatin (or Carboplatin AUC 5)",
                "category": "Chemotherapy",
                "class": "Platinum Alkylating DNA Cross-Linker",
                "dosage": "75 mg/m² IV on Day 1 of 21-day cycle x 4 cycles",
                "role": "Binds DNA forming intra-strand cross-links that trigger apoptotic tumor cell death."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (Taxol)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "200 mg/m² IV Day 1 of 21-day cycle x 4 cycles",
                "role": "Microtubule hyperstabilization complementing platinum DNA damage."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "16 mg IV 30 min prior to Cisplatin + 8 mg PO Q12H x 3 days",
                "role": "Strict antiemetic control against high-emetogenic platinum."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "12-20 mg IV pre-medication",
                "role": "Synergistic emesis blockade and prevention of paclitaxel hypersensitivity."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20 mg PO daily",
                "role": "Gastric mucosa protection during corticosteroid pulse."
            }
        ],
        "all_item_ids": ["cisplatin", "paclitaxel", "ondansetron", "dexamethasone", "omeprazole"],
        "contraindicated_supplements": [
            {
                "name": "Ibuprofen / NSAIDs",
                "hazard": "Renal Hemodynamic Competition: Combined with Cisplatin, dramatically triggers acute tubular necrosis (ATN) and severe nephrotoxicity."
            },
            {
                "name": "Green Tea Extract (High-Dose EGCG)",
                "hazard": "EGCG acts as an off-target ligand competing with platinum cellular transport."
            },
            {
                "name": "St. John's Wort",
                "hazard": "CYP3A4 acceleration of taxane partner."
            }
        ],
        "safe_remedies_and_habits": [
            "Aggressive pre- and post-infusion saline hydration (minimum 3 liters/day) for renal clearance",
            "Monitor serum creatinine, BUN, and audiometric hearing tests prior to each cycle",
            "Ginger root tea for post-infusion delayed nausea"
        ]
    },
    "lung_stage_iii": {
        "cancer_type": "lung",
        "cancer_name": "Lung Cancer",
        "stage": "Stage III",
        "stage_label": "Locally Advanced / Mediastinal Nodal NSCLC (Stage IIIA/B/C)",
        "protocol_name": "Definitive Concurrent Chemoradiation (CCRT) + Consolidation Immunotherapy",
        "clinical_intent": "Locally Advanced Curative-Intent Eradication & Immune Consolidation",
        "evidence_guideline": "PACIFIC Trial & NCCN Category 1 Definitive Chemoradiation",
        "prescribed_core_drugs": [
            {
                "id": "carboplatin",
                "name": "Carboplatin",
                "category": "Chemotherapy",
                "class": "Platinum Agent",
                "dosage": "AUC 2 IV weekly x 6-7 weeks concurrent with thoracic radiation (60-66 Gy)",
                "role": "Radiation sensitizer inducing localized DNA breaks."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (Taxol)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "45-50 mg/m² IV weekly concurrent with radiation",
                "role": "Arrests tumor cells in G2/M phase, the most radiosensitive stage of cell cycle."
            },
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda / Durvalumab)",
                "category": "Immunotherapy",
                "class": "PD-1/PD-L1 Immune Checkpoint Inhibitor",
                "dosage": "Consolidation IV Q3W for up to 12 months post-CCRT",
                "role": "Prevents systemic distant dissemination by revitalizing exhausted CD8+ T-cells."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO prior to each chemo infusion",
                "role": "Antiemetic control."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "8 mg IV weekly pre-medication",
                "role": "Radiation pneumonitis and hypersensitivity reduction."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20-40 mg PO daily",
                "role": "Management of radiation-induced esophagitis and reflux."
            }
        ],
        "all_item_ids": ["carboplatin", "paclitaxel", "pembrolizumab", "ondansetron", "dexamethasone", "omeprazole"],
        "contraindicated_supplements": [
            {
                "name": "High-Dose Vitamin C (>2000mg) & Vitamin E",
                "hazard": "Radiation Therapy Neutralization: Radiation works by generating reactive oxygen free radicals to tear cancer DNA apart. High-dose antioxidants scavenge these radicals and shield malignant cells."
            },
            {
                "name": "St. John's Wort",
                "hazard": "P-gp and CYP3A4 induction disrupts systemic paclitaxel AUC."
            }
        ],
        "safe_remedies_and_habits": [
            "Soft, bland, non-acidic protein smoothies with flaxseed meal to ease radiation esophagitis",
            "Monitor pulse oximetry (SpO2) daily to detect early radiation pneumonitis",
            "Avoid direct chest sun exposure; use plain calendula or water-based gels on irradiated skin"
        ]
    },
    "lung_stage_iv": {
        "cancer_type": "lung",
        "cancer_name": "Lung Cancer",
        "stage": "Stage IV",
        "stage_label": "Metastatic Non-Small Cell Lung Cancer (TanyNanyM1a/b/c)",
        "protocol_name": "First-Line Chemo-Immunotherapy (KEYNOTE-189 / KEYNOTE-407)",
        "clinical_intent": "Systemic Disease Stabilization, Survival Extension & Palliative Maintenance",
        "evidence_guideline": "NCCN Category 1 Preferred First-Line Systemic Regimen for Metastatic NSCLC",
        "prescribed_core_drugs": [
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda)",
                "category": "Immunotherapy",
                "class": "PD-1 Immune Checkpoint Inhibitor",
                "dosage": "200 mg IV Q3W (or 400 mg IV Q6W) for up to 2 years",
                "role": "Maintains durable anti-tumor immunologic surveillance across visceral and bone sites."
            },
            {
                "id": "carboplatin",
                "name": "Carboplatin",
                "category": "Chemotherapy",
                "class": "Platinum Agent",
                "dosage": "AUC 5 IV Q3W x 4 cycles",
                "role": "Rapid debulking of metastatic tumor mass and neoantigen release."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (or Pemetrexed)",
                "category": "Chemotherapy",
                "class": "Taxane / Antimetabolite",
                "dosage": "175 mg/m² IV Q3W x 4 cycles",
                "role": "Complementary cytotoxic cytoreduction."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO Q8H PRN",
                "role": "Nausea management."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "8 mg IV on chemo infusion days",
                "role": "Emesis and hypersensitivity pre-medication."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO nightly",
                "role": "Fatigue reduction and sleep architecture stabilization."
            }
        ],
        "all_item_ids": ["pembrolizumab", "carboplatin", "paclitaxel", "ondansetron", "dexamethasone", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates clearance of systemic cytotoxic and targeted backbone."
            },
            {
                "name": "Ginkgo Biloba & High-Dose Garlic",
                "hazard": "Exacerbates hemoptysis and pulmonary mucosal bleeding in patients with central tumors or thrombocytopenia."
            }
        ],
        "safe_remedies_and_habits": [
            "Palliative respiratory therapy with gentle portable oxygen titration if SpO2 <92%",
            "Nutritional calorie-dense shakes with medium-chain triglycerides (MCTs)",
            "Active psycho-oncology support and caregiver respite planning"
        ]
    },

    # ------------------ BRAIN TUMORS ------------------
    "brain_stage_0": {
        "cancer_type": "brain",
        "cancer_name": "Brain Tumor",
        "stage": "Stage 0",
        "stage_label": "Benign / Low-Grade Cranial Finding (Grade I / Pituitary Microadenoma)",
        "protocol_name": "Neuro-Radiological Watchful Surveillance Protocol",
        "clinical_intent": "Non-Invasive Observation & Neurological Symptom Surveillance",
        "evidence_guideline": "WHO Classification of CNS Tumors (2021) & NCCN Guidelines",
        "prescribed_core_drugs": [],
        "prescribed_supportive_drugs": [
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO nightly",
                "role": "Regulates sleep-wake cycles and supports neurological homeostasis."
            },
            {
                "id": "ginger_root",
                "name": "Ginger Root Infusion",
                "category": "Herbal Supplement",
                "class": "Natural Anti-Nausea",
                "dosage": "1 cup daily as needed",
                "role": "Soothes mild motion sensitivity and transient headache nausea."
            }
        ],
        "all_item_ids": ["melatonin", "ginger_root"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba",
                "hazard": "Potent anti-platelet activating factor (PAF) activity increases spontaneous intracranial hemorrhage risk."
            }
        ],
        "safe_remedies_and_habits": [
            "Baseline high-resolution brain MRI with contrast every 6-12 months",
            "Prompt evaluation of visual fields and neurological acuity",
            "Stress-reduction mindfulness and avoidance of intense valsalva maneuvers"
        ]
    },
    "brain_stage_i": {
        "cancer_type": "brain",
        "cancer_name": "Brain Tumor",
        "stage": "Stage I",
        "stage_label": "Low-Grade Well-Circumscribed Astrocytoma / Meningioma",
        "protocol_name": "Post-Resection Neuro-Oncology Surveillance & Anti-Edema Prophylaxis",
        "clinical_intent": "Curative Localized Decompression & Neurological Preservation",
        "evidence_guideline": "EANO / NCCN CNS Guidelines for Low-Grade Glioma",
        "prescribed_core_drugs": [
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "2-4 mg PO daily (tapered based on clinical edema)",
                "role": "Restores blood-brain barrier integrity, drastically suppressing vasogenic cerebral edema."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20 mg PO daily",
                "role": "Essential prophylaxis against corticosteroid-induced peptic ulcer disease."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO nightly",
                "role": "Neuro-protective circadian maintenance."
            }
        ],
        "all_item_ids": ["dexamethasone", "omeprazole", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba",
                "hazard": "Direct Antiplatelet Action: Drastically elevates risk of postoperative subdural or parenchymal hematoma formation."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Alters corticosteroid and anticonvulsant metabolism."
            }
        ],
        "safe_remedies_and_habits": [
            "Maintain seizure precaution guidelines (supervised swimming, avoid driving until cleared)",
            "Frequent head-of-bed elevation (30 degrees) to assist cranial venous drainage",
            "Neuro-cognitive rehabilitation exercises and memory puzzles"
        ]
    },
    "brain_stage_ii": {
        "cancer_type": "brain",
        "cancer_name": "Brain Tumor",
        "stage": "Stage II",
        "stage_label": "Diffuse Low-Grade Infiltrative Glioma / Oligodendroglioma",
        "protocol_name": "Intermediate Alkylating Temozolomide Chemotherapy Protocol",
        "clinical_intent": "Inhibition of Diffuse Parenchymal Invasion & Delay of Malignant Transformation",
        "evidence_guideline": "RTOG 9802 & NCCN Category 1 for High-Risk Grade II Glioma",
        "prescribed_core_drugs": [
            {
                "id": "temozolomide",
                "name": "Temozolomide (Temodar)",
                "category": "Chemotherapy",
                "class": "Oral Alkylating Imidazotetrazine",
                "dosage": "150-200 mg/m² PO once daily on Days 1-5 of 28-day cycle x 6-12 cycles",
                "role": "Crosses the blood-brain barrier effortlessly and methylates DNA at O6/N7 positions of guanine."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO 60 mins before each Temozolomide dose",
                "role": "Obligate prophylaxis against acute emesis caused by oral alkylating agent."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "2-4 mg PO daily PRN for neurological focal deficit",
                "role": "Control of peritumoral vasogenic edema."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "20 mg PO daily",
                "role": "Gastric mucosa protection."
            }
        ],
        "all_item_ids": ["temozolomide", "ondansetron", "dexamethasone", "omeprazole"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba & Allicin Garlic",
                "hazard": "Intracranial Hemorrhage Hazard: Infiltrative brain tumors possess fragile neo-vasculature; herbal platelet inhibitors trigger catastrophic hemorrhagic stroke."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates clearance of supportive antiemetics and corticosteroids."
            }
        ],
        "safe_remedies_and_habits": [
            "Take Temozolomide on an empty stomach at bedtime to minimize nausea",
            "Monitor complete blood count (CBC) with differential weekly on Days 22-28 (nadir period)",
            "Low-glycemic Mediterranean nutrition to minimize cerebral edema fluctuations"
        ]
    },
    "brain_stage_iii": {
        "cancer_type": "brain",
        "cancer_name": "Brain Tumor",
        "stage": "Stage III",
        "stage_label": "Anaplastic Astrocytoma / High-Grade Malignant Glioma (Grade III)",
        "protocol_name": "Focal Chemoradiation with Concurrent & Maintenance Temozolomide",
        "clinical_intent": "Maximum Cytoreduction, Prolongation of Progression-Free Survival",
        "evidence_guideline": "CATNON Trial & NCCN Category 1 Protocol for Anaplastic Gliomas",
        "prescribed_core_drugs": [
            {
                "id": "temozolomide",
                "name": "Temozolomide (Temodar)",
                "category": "Chemotherapy",
                "class": "Oral Alkylating Imidazotetrazine",
                "dosage": "75 mg/m² PO daily x 42 days concurrent with RT, then 150-200 mg/m² Days 1-5 Q28D x 12 cycles",
                "role": "Induces cytotoxic DNA O6-methylguanine adducts leading to double-strand breaks during DNA replication."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO 60 mins before each Temozolomide dose",
                "role": "Antiemetic coverage."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "4-8 mg PO daily in divided doses",
                "role": "Intensive vasogenic edema mitigation."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO nightly",
                "role": "Neuroprotective sleep architecture preservation."
            }
        ],
        "all_item_ids": ["temozolomide", "ondansetron", "dexamethasone", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba",
                "hazard": "Severe bleeding diathesis inside necrotic or irradiated cranial tumor bed."
            },
            {
                "name": "High-Dose Vitamin C (>2000mg/day)",
                "hazard": "Interferes with radiation-induced reactive oxygen species (ROS) cell kill."
            }
        ],
        "safe_remedies_and_habits": [
            "Prophylactic Trimethoprim-Sulfamethoxazole for PCP during concurrent chemoradiation with dexamethasone",
            "Cognitive pacing and scheduled afternoon quiet rest periods",
            "Strict blood sugar tracking (steroid-induced hyperglycemia control)"
        ]
    },
    "brain_stage_iv": {
        "cancer_type": "brain",
        "cancer_name": "Brain Tumor",
        "stage": "Stage IV",
        "stage_label": "Glioblastoma Multiforme (GBM - WHO Grade IV)",
        "protocol_name": "Stupp Protocol (Concurrent Temozolomide + Radiotherapy -> Adjuvant TMZ)",
        "clinical_intent": "Maximum Prolongation of Overall Survival & Preservation of Neuro-Cognitive Status",
        "evidence_guideline": "Stupp et al. (NEJM) & NCCN Preferred Category 1 Standard of Care for Glioblastoma",
        "prescribed_core_drugs": [
            {
                "id": "temozolomide",
                "name": "Temozolomide (Temodar)",
                "category": "Chemotherapy",
                "class": "Oral Alkylating Imidazotetrazine",
                "dosage": "75 mg/m² PO daily x 42 days with 60 Gy IMRT, followed by 150-200 mg/m² PO Days 1-5 Q28D x 6-12 cycles",
                "role": "Crosses the blood-brain barrier rapidly; produces lethal DNA O6-methylguanine lesions that trigger catastrophic glioma cell apoptosis."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO 60 mins before each Temozolomide dose",
                "role": "Prevents daily emesis and preserves oral adherence."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "4-16 mg PO daily (titrated to minimum effective dose for intracranial mass effect)",
                "role": "Reduces life-threatening intracranial pressure and peritumoral edema."
            },
            {
                "id": "omeprazole",
                "name": "Omeprazole",
                "category": "Prescription OTC",
                "class": "Proton Pump Inhibitor",
                "dosage": "40 mg PO daily",
                "role": "Prevents severe steroid-induced gastroduodenal ulceration."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO at bedtime",
                "role": "Mitigates corticosteroid insomnia and supports circadian rhythm."
            }
        ],
        "all_item_ids": ["temozolomide", "ondansetron", "dexamethasone", "omeprazole", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba Extract",
                "hazard": "FATAL INTRACRANIAL BLEED HAZARD: GBMs possess extreme vascular proliferation and fragile arteriovenous malformations. Ginkgo's PAF antagonism causes spontaneous intratumoral hemorrhage."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates clearance of dexamethasone and anticonvulsants, precipitating uncontrolled seizures and brain herniation."
            },
            {
                "name": "High-Dose Vitamin C / E Megadoses",
                "hazard": "Scavenges therapeutic ROS free radicals generated by 60 Gy radiation beam."
            }
        ],
        "safe_remedies_and_habits": [
            "Tumor Treating Fields (Optune / TTFields) wearable therapy for alternating electric field disruption",
            "Physical and speech rehabilitation therapy with dedicated family caregiver coaching",
            "Ketogenic/low-carb Mediterranean meals under direct clinical oncology nutrition guidance"
        ]
    },

    # ------------------ SKIN CANCER (MELANOMA) ------------------
    "skin_stage_0": {
        "cancer_type": "skin",
        "cancer_name": "Skin Cancer",
        "stage": "Stage 0",
        "stage_label": "Melanoma In-Situ / Lentigo Maligna (TisN0M0)",
        "protocol_name": "Wide Local Excision Margin Clearance & Nicotinamide Photoprotection",
        "clinical_intent": "Curative Surgical Resection & Lifetime Secondary Prevention",
        "evidence_guideline": "NCCN Cutaneous Melanoma Guidelines (v1.2024)",
        "prescribed_core_drugs": [],
        "prescribed_supportive_drugs": [
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone / Antioxidant",
                "dosage": "3 mg PO nightly",
                "role": "Supports nocturnal cellular DNA excision repair in cutaneous tissue."
            }
        ],
        "all_item_ids": ["melatonin"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Causes extreme cutaneous photosensitization (hypericin-mediated solar dermatitis) and increases ultraviolet dermal burn vulnerability."
            }
        ],
        "safe_remedies_and_habits": [
            "Strict daily broad-spectrum SPF 50+ mineral sunscreen (Zinc Oxide / Titanium Dioxide)",
            "Oral Nicotinamide (Vitamin B3 500 mg twice daily) to replenish cellular NAD+ and reduce non-melanoma skin cancer recurrence by 23%",
            "Total-body digital dermoscopy skin examination every 3-6 months"
        ]
    },
    "skin_stage_i": {
        "cancer_type": "skin",
        "cancer_name": "Skin Cancer",
        "stage": "Stage I",
        "stage_label": "Early Invasive Melanoma (T1a/b N0M0, Breslow Depth ≤1.0mm)",
        "protocol_name": "Surgical Margin Clearance & Sentinel Lymph Node Biopsy Protocol",
        "clinical_intent": "Definitive Curative Surgical Eradication & Lymphatic Staging",
        "evidence_guideline": "AJCC 8th Edition & NCCN Clinical Guidelines",
        "prescribed_core_drugs": [],
        "prescribed_supportive_drugs": [
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO nightly",
                "role": "Cellular circadian regulation and immune homeostasis."
            }
        ],
        "all_item_ids": ["melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba & High-Dose Garlic Extract",
                "hazard": "Increases postoperative bleeding, seroma, and hematoma complications at surgical wide excision and sentinel lymph node biopsy sites."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Causes cutaneous photosensitivity reactions."
            }
        ],
        "safe_remedies_and_habits": [
            "Wear UPF 50+ UV-protective clothing, wide-brimmed hats, and UV400 sunglasses",
            "Avoid midday outdoor UV exposure between 10 AM and 4 PM",
            "Monthly patient partner-assisted skin self-examination (ABCDE melanoma rule)"
        ]
    },
    "skin_stage_ii": {
        "cancer_type": "skin",
        "cancer_name": "Skin Cancer",
        "stage": "Stage II",
        "stage_label": "Deep / Ulcerated High-Risk Melanoma (T2b-T4b N0M0)",
        "protocol_name": "Adjuvant Immune Checkpoint Inhibition Protocol (KEYNOTE-716)",
        "clinical_intent": "Adjuvant Recurrence-Free Survival (RFS) Prolongation in High-Risk Resected Melanoma",
        "evidence_guideline": "FDA Approved & NCCN Category 1 for High-Risk Stage IIB/C Melanoma",
        "prescribed_core_drugs": [
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda)",
                "category": "Immunotherapy",
                "class": "PD-1 Immune Checkpoint Inhibitor",
                "dosage": "200 mg IV Q3W (or 400 mg IV Q6W) for up to 12 months",
                "role": "Blocks the PD-1/PD-L1 inhibitory checkpoint, re-energizing cytotoxic T-cells to seek out and destroy occult disseminated micrometastatic melanoma cells."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "3 mg PO nightly",
                "role": "Supports circadian rhythm and mitigates immunotherapy-related fatigue."
            }
        ],
        "all_item_ids": ["pembrolizumab", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "St. John's Wort",
                "hazard": "Induces metabolic instability and photosensitivity during active immunotherapy."
            },
            {
                "name": "High-Dose Immunosuppressive Herbs",
                "hazard": "Blunts T-cell immune checkpoint activation needed for curative eradication."
            }
        ],
        "safe_remedies_and_habits": [
            "Serial thyroid and pituitary endocrine panel monitoring (TSH, free T4, ACTH) before every cycle",
            "Prompt reporting of dry cough (pneumonitis) or severe diarrhea (colitis)",
            "Strict sun safety and skin hydration with pure unscented aloe vera"
        ]
    },
    "skin_stage_iii": {
        "cancer_type": "skin",
        "cancer_name": "Skin Cancer",
        "stage": "Stage III",
        "stage_label": "Regional Lymph Node Positive / In-Transit Metastatic Melanoma",
        "protocol_name": "Adjuvant Systemic Anti-PD-1 Immunotherapy Protocol",
        "clinical_intent": "Adjuvant Systemic Clearance of Nodal & Regional Metastases",
        "evidence_guideline": "KEYNOTE-054 & CheckMate-238 Trials (NCCN Category 1)",
        "prescribed_core_drugs": [
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda)",
                "category": "Immunotherapy",
                "class": "PD-1 Immune Checkpoint Inhibitor",
                "dosage": "200 mg IV Q3W for 12 months",
                "role": "Maintains persistent systemic anti-melanoma T-cell clonal expansion."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO PRN for infusion nausea",
                "role": "Symptom control."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO nightly",
                "role": "Reduces fatigue and sleep disruption."
            }
        ],
        "all_item_ids": ["pembrolizumab", "ondansetron", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba & Warfarin Conflicts",
                "hazard": "Hemorrhagic risk around lymph node dissection beds."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Phototoxic dermatitis and metabolic perturbation."
            }
        ],
        "safe_remedies_and_habits": [
            "Lymphatic drainage massage to prevent postoperative lymphedema in dissection extremities",
            "Cross-sectional surveillance PET-CT / Brain MRI every 4-6 months",
            "Diet rich in dietary fiber and prebiotics to nurture optimal gut microbiome for immunotherapy response"
        ]
    },
    "skin_stage_iv": {
        "cancer_type": "skin",
        "cancer_name": "Skin Cancer",
        "stage": "Stage IV",
        "stage_label": "Distant Visceral / Brain / Skeletal Metastatic Melanoma (M1a-d)",
        "protocol_name": "Dual Immune Checkpoint Blockade & Systemic Targeted Protocol",
        "clinical_intent": "Durable Long-Term Systemic Remission & Overall Survival Maximization",
        "evidence_guideline": "CheckMate-067 & NCCN Preferred Category 1 Regimen",
        "prescribed_core_drugs": [
            {
                "id": "pembrolizumab",
                "name": "Pembrolizumab (Keytruda)",
                "category": "Immunotherapy",
                "class": "PD-1 Immune Checkpoint Inhibitor",
                "dosage": "200 mg IV Q3W (or combined with anti-CTLA4 Ipilimumab)",
                "role": "Achieves unprecedented durable 5-year survival rates exceeding 50% in metastatic melanoma."
            },
            {
                "id": "paclitaxel",
                "name": "Paclitaxel (Taxol - if cytotoxic salvage required)",
                "category": "Chemotherapy",
                "class": "Taxane Microtubule Stabilizer",
                "dosage": "175 mg/m² IV Q3W (second-line rescue)",
                "role": "Cytoreductive taxane for rapid symptomatic visceral burden."
            }
        ],
        "prescribed_supportive_drugs": [
            {
                "id": "ondansetron",
                "name": "Ondansetron (Zofran)",
                "category": "Supportive Care",
                "class": "5-HT3 Antagonist",
                "dosage": "8 mg PO Q8H PRN",
                "role": "Antiemetic control."
            },
            {
                "id": "dexamethasone",
                "name": "Dexamethasone",
                "category": "Supportive Care",
                "class": "Corticosteroid",
                "dosage": "Reserved strictly for Grade ≥2 immune-related adverse events (irAEs)",
                "role": "First-line rescue agent for autoimmune colitis, pneumonitis, or hepatitis."
            },
            {
                "id": "melatonin",
                "name": "Melatonin",
                "category": "Dietary Supplement",
                "class": "Neurohormone",
                "dosage": "5 mg PO at bedtime",
                "role": "Fatigue and sleep support."
            }
        ],
        "all_item_ids": ["pembrolizumab", "paclitaxel", "ondansetron", "melatonin"],
        "contraindicated_supplements": [
            {
                "name": "Ginkgo Biloba & High-Dose Curcumin",
                "hazard": "Extremely hazardous bleeding diathesis in patients with brain or visceral metastases."
            },
            {
                "name": "St. John's Wort",
                "hazard": "Accelerates clearance of paclitaxel and supportive drugs."
            }
        ],
        "safe_remedies_and_habits": [
            "Immediate reporting of autoimmune immune-related side effects (rash, diarrhea, shortness of breath)",
            "Nutrient-dense Mediterranean diet with olive oil, fatty fish, and colorful polyphenols",
            "Palliative care and psycho-oncology integration from the first cycle"
        ]
    }
}


def get_prescribed_regimen(cancer_type: str, stage: str) -> Dict[str, Any]:
    """
    Returns an evidence-based oncology prescription (core drugs, supportive drugs,
    clinical intent, dosages, contraindicated supplements, and health habits)
    based on the diagnosed cancer type and stage.
    """
    c_type = (cancer_type or "breast").lower().strip()
    if c_type not in ["breast", "lung", "brain", "skin"]:
        c_type = "breast"

    stg = normalize_stage_code(stage)
    key = f"{c_type}_{stg.lower().replace(' ', '_')}"

    prescription = ONCOLOGY_STAGE_PRESCRIPTIONS.get(key)
    if not prescription:
        fallback_key = f"{c_type}_stage_i"
        prescription = ONCOLOGY_STAGE_PRESCRIPTIONS.get(fallback_key, ONCOLOGY_STAGE_PRESCRIPTIONS["breast_stage_i"])

    return prescription

