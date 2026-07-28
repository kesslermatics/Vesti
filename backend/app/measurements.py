"""Definition der Koerpermasse inkl. Mess-Anleitungen fuer das Profil."""

# Jedes Mass mit Label, Einheit, Anleitung und optionalem Tipp
MEASUREMENT_FIELDS = [
    {
        "key": "height",
        "label": "Körpergröße",
        "unit": "cm",
        "group": "Basis",
        "how": "Stell dich ohne Schuhe gerade an eine Wand, Fersen an der Wand. Markiere die höchste Stelle deines Kopfes und miss vom Boden bis zur Markierung.",
        "tip": "Am besten abends messen – morgens ist man minimal größer.",
    },
    {
        "key": "weight",
        "label": "Gewicht",
        "unit": "kg",
        "group": "Basis",
        "how": "Wiege dich morgens nach dem Aufstehen, nüchtern und ohne Kleidung.",
        "tip": "Nur relevant für Größen-Empfehlungen, völlig optional.",
    },
    {
        "key": "chest",
        "label": "Brustumfang",
        "unit": "cm",
        "group": "Oberkörper",
        "how": "Miss um die stärkste Stelle deiner Brust, das Maßband waagerecht unter den Armen durch. Atme normal aus.",
        "tip": "Das Maßband soll anliegen, aber nicht einschnüren.",
    },
    {
        "key": "waist",
        "label": "Taillenumfang",
        "unit": "cm",
        "group": "Oberkörper",
        "how": "Miss um die schmalste Stelle deines Oberkörpers, meist etwa 2–3 cm über dem Bauchnabel.",
        "tip": "Bauch nicht einziehen – normal stehen und ausatmen.",
    },
    {
        "key": "hips",
        "label": "Hüftumfang",
        "unit": "cm",
        "group": "Unterkörper",
        "how": "Miss um die breiteste Stelle von Hüfte und Gesäß, Füße zusammen.",
        "tip": "Das Maßband muss vorne und hinten auf gleicher Höhe liegen.",
    },
    {
        "key": "shoulder",
        "label": "Schulterbreite",
        "unit": "cm",
        "group": "Oberkörper",
        "how": "Miss über den Rücken von der äußeren Kante der einen Schulter zur anderen.",
        "tip": "Am einfachsten mit Hilfe einer zweiten Person oder anhand eines gut passenden Hemdes.",
    },
    {
        "key": "sleeve_length",
        "label": "Ärmellänge",
        "unit": "cm",
        "group": "Oberkörper",
        "how": "Arm leicht anwinkeln. Miss von der Schulternaht über den Ellenbogen bis zum Handgelenk.",
        "tip": "Für Hemden entscheidend – lieber zweimal messen.",
    },
    {
        "key": "neck",
        "label": "Halsumfang",
        "unit": "cm",
        "group": "Oberkörper",
        "how": "Miss um den Hals dort, wo normalerweise der Hemdkragen sitzt.",
        "tip": "Zwei Finger sollten noch zwischen Maßband und Hals passen.",
    },
    {
        "key": "inseam",
        "label": "Innenbeinlänge",
        "unit": "cm",
        "group": "Unterkörper",
        "how": "Miss vom Schritt an der Innenseite des Beins bis zum Knöchel.",
        "tip": "Alternativ eine gut sitzende Hose flach hinlegen und die Innennaht messen.",
    },
    {
        "key": "outseam",
        "label": "Außenbeinlänge",
        "unit": "cm",
        "group": "Unterkörper",
        "how": "Miss von der Taille an der Außenseite des Beins bis zum Knöchel.",
        "tip": "Bestimmt, wie lang eine Hose an dir wirkt.",
    },
    {
        "key": "thigh",
        "label": "Oberschenkelumfang",
        "unit": "cm",
        "group": "Unterkörper",
        "how": "Miss um die stärkste Stelle des Oberschenkels, direkt unter dem Schritt.",
        "tip": "Wichtig bei Slim-Fit-Hosen und Jeans.",
    },
]

# Konfektionsgroessen die der Nutzer angeben kann
SIZE_FIELDS = [
    {
        "key": "size_top",
        "label": "Oberteil-Größe",
        "options": ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL"],
    },
    {
        "key": "size_bottom",
        "label": "Hosengröße",
        "placeholder": "z.B. 32/34 oder 48",
    },
    {
        "key": "size_shoe",
        "label": "Schuhgröße",
        "placeholder": "z.B. 43 oder 9.5",
    },
    {
        "key": "size_shirt",
        "label": "Hemdgröße",
        "placeholder": "z.B. 41 oder M",
    },
]

# Passform-Vorlieben
FIT_PREFERENCES = [
    "sehr eng",
    "slim fit",
    "regular",
    "relaxed",
    "oversized",
]

BODY_TYPES = [
    "schlank",
    "athletisch",
    "durchschnittlich",
    "kräftig",
    "kurvig",
]
