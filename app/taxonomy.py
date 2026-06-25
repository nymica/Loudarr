from collections import OrderedDict

# Broad category → sub-genres
# Each sub: (Display Name, [search tags, first is primary])
TAXONOMY = OrderedDict([
    ("Rock", {
        "tag": "rock",
        "subs": [
            ("Classic Rock",        ["classic rock"]),
            ("Alternative Rock",    ["alternative rock", "alternative"]),
            ("Indie Rock",          ["indie rock", "indie"]),
            ("Progressive Rock",    ["progressive rock", "prog rock"]),
            ("Hard Rock",           ["hard rock"]),
            ("Folk Rock",           ["folk rock"]),
            ("Psychedelic Rock",    ["psychedelic rock", "psychedelic"]),
            ("Post-Rock",           ["post-rock"]),
            ("Southern Rock",       ["southern rock"]),
            ("Garage Rock",         ["garage rock"]),
            ("Art Rock",            ["art rock"]),
            ("Glam Rock",           ["glam rock"]),
        ],
    }),
    ("Metal", {
        "tag": "metal",
        "subs": [
            ("Heavy Metal",         ["heavy metal"]),
            ("Thrash Metal",        ["thrash metal"]),
            ("Death Metal",         ["death metal"]),
            ("Black Metal",         ["black metal"]),
            ("Doom Metal",          ["doom metal"]),
            ("Power Metal",         ["power metal"]),
            ("Progressive Metal",   ["progressive metal"]),
            ("Symphonic Metal",     ["symphonic metal"]),
            ("Folk Metal",          ["folk metal"]),
            ("Metalcore",           ["metalcore"]),
            ("Nu-Metal",            ["nu-metal", "nu metal"]),
            ("Sludge Metal",        ["sludge metal"]),
            ("Post-Metal",          ["post-metal"]),
            ("Groove Metal",        ["groove metal"]),
        ],
    }),
    ("Punk", {
        "tag": "punk",
        "subs": [
            ("Hardcore Punk",       ["hardcore punk", "hardcore"]),
            ("Pop Punk",            ["pop punk"]),
            ("Post-Punk",           ["post-punk"]),
            ("Ska Punk",            ["ska punk"]),
            ("Emo",                 ["emo"]),
            ("Anarcho-Punk",        ["anarcho-punk"]),
            ("Crust Punk",          ["crust punk"]),
            ("Screamo",             ["screamo"]),
        ],
    }),
    ("Pop", {
        "tag": "pop",
        "subs": [
            ("Synth-Pop",           ["synth-pop", "synthpop"]),
            ("Indie Pop",           ["indie pop"]),
            ("Dream Pop",           ["dream pop"]),
            ("Electropop",          ["electropop"]),
            ("Power Pop",           ["power pop"]),
            ("Art Pop",             ["art pop"]),
            ("Baroque Pop",         ["baroque pop"]),
            ("Chamber Pop",         ["chamber pop"]),
            ("Bubblegum",           ["bubblegum pop", "bubblegum"]),
            ("K-Pop",               ["k-pop", "kpop"]),
            ("J-Pop",               ["j-pop", "jpop"]),
        ],
    }),
    ("Electronic", {
        "tag": "electronic",
        "subs": [
            ("Ambient",             ["ambient"]),
            ("House",               ["house"]),
            ("Techno",              ["techno"]),
            ("Trance",              ["trance"]),
            ("IDM",                 ["idm"]),
            ("Drum and Bass",       ["drum and bass"]),
            ("Synthwave",           ["synthwave"]),
            ("Dubstep",             ["dubstep"]),
            ("Industrial",          ["industrial"]),
            ("Downtempo",           ["downtempo"]),
            ("Trip-Hop",            ["trip-hop"]),
            ("Chillwave",           ["chillwave"]),
            ("Electronica",         ["electronica"]),
            ("Noise",               ["noise"]),
            ("Glitch",              ["glitch"]),
            ("EBM",                 ["electronic body music", "ebm"]),
        ],
    }),
    ("Hip-Hop", {
        "tag": "hip-hop",
        "subs": [
            ("Boom Bap",            ["boom bap"]),
            ("Trap",                ["trap"]),
            ("Alternative Hip-Hop", ["alternative hip hop"]),
            ("East Coast",          ["east coast hip hop"]),
            ("West Coast",          ["west coast hip hop"]),
            ("Jazz Rap",            ["jazz rap"]),
            ("Southern Hip-Hop",    ["southern hip hop"]),
            ("Cloud Rap",           ["cloud rap"]),
            ("Conscious Hip-Hop",   ["conscious hip hop"]),
            ("Gangsta Rap",         ["gangsta rap"]),
            ("G-Funk",              ["g-funk"]),
        ],
    }),
    ("R&B / Soul", {
        "tag": "soul",
        "subs": [
            ("Soul",                ["soul"]),
            ("Funk",                ["funk"]),
            ("Motown",              ["motown"]),
            ("Neo-Soul",            ["neo-soul"]),
            ("Contemporary R&B",    ["r&b"]),
            ("Quiet Storm",         ["quiet storm"]),
            ("Disco",               ["disco"]),
            ("New Jack Swing",      ["new jack swing"]),
        ],
    }),
    ("Country", {
        "tag": "country",
        "subs": [
            ("Classic Country",     ["classic country", "traditional country"]),
            ("Alternative Country", ["alternative country"]),
            ("Outlaw Country",      ["outlaw country"]),
            ("Country Pop",         ["country pop"]),
            ("Bluegrass",           ["bluegrass"]),
            ("Americana",           ["americana"]),
            ("Honky Tonk",          ["honky tonk"]),
            ("Country Rock",        ["country rock"]),
            ("Cowboy",              ["cowboy", "western"]),
        ],
    }),
    ("Jazz", {
        "tag": "jazz",
        "subs": [
            ("Bebop",               ["bebop"]),
            ("Smooth Jazz",         ["smooth jazz"]),
            ("Free Jazz",           ["free jazz"]),
            ("Jazz Fusion",         ["jazz fusion"]),
            ("Cool Jazz",           ["cool jazz"]),
            ("Soul Jazz",           ["soul jazz"]),
            ("Vocal Jazz",          ["vocal jazz"]),
            ("Bossa Nova",          ["bossa nova"]),
            ("Contemporary Jazz",   ["contemporary jazz"]),
            ("Swing",               ["swing"]),
            ("Big Band",            ["big band"]),
        ],
    }),
    ("Blues", {
        "tag": "blues",
        "subs": [
            ("Delta Blues",         ["delta blues"]),
            ("Electric Blues",      ["electric blues"]),
            ("Chicago Blues",       ["chicago blues"]),
            ("Blues Rock",          ["blues rock"]),
            ("Acoustic Blues",      ["acoustic blues"]),
            ("Texas Blues",         ["texas blues"]),
            ("British Blues",       ["british blues"]),
        ],
    }),
    ("Folk / Acoustic", {
        "tag": "folk",
        "subs": [
            ("Singer-Songwriter",   ["singer-songwriter"]),
            ("Traditional Folk",    ["folk"]),
            ("Celtic",              ["celtic"]),
            ("Americana",           ["americana"]),
            ("Acoustic",            ["acoustic"]),
            ("Neofolk",             ["neofolk"]),
            ("Freak Folk",          ["freak folk"]),
            ("Appalachian",         ["appalachian"]),
        ],
    }),
    ("Christian / Gospel", {
        "tag": "christian music",
        "subs": [
            ("Contemporary Christian", ["contemporary christian music", "ccm"]),
            ("Christian Rock",      ["christian rock"]),
            ("Christian Metal",     ["christian metal"]),
            ("Worship",             ["worship"]),
            ("Gospel",              ["gospel"]),
            ("Christian Rap",       ["christian hip hop", "christian rap"]),
            ("Praise & Worship",    ["praise and worship"]),
            ("Southern Gospel",     ["southern gospel"]),
        ],
    }),
    ("Classical", {
        "tag": "classical",
        "subs": [
            ("Baroque",             ["baroque"]),
            ("Romantic",            ["romantic"]),
            ("Modern Classical",    ["modern classical"]),
            ("Contemporary Classical", ["contemporary classical"]),
            ("Opera",               ["opera"]),
            ("Orchestral",          ["orchestral"]),
            ("Chamber Music",       ["chamber music"]),
            ("Piano",               ["piano"]),
            ("Choral",              ["choral"]),
            ("Minimalism",          ["minimalism", "minimal"]),
        ],
    }),
    ("Reggae / Ska", {
        "tag": "reggae",
        "subs": [
            ("Reggae",              ["reggae"]),
            ("Ska",                 ["ska"]),
            ("Dub",                 ["dub"]),
            ("Dancehall",           ["dancehall"]),
            ("Rocksteady",          ["rocksteady"]),
            ("Roots Reggae",        ["roots reggae"]),
        ],
    }),
    ("Latin", {
        "tag": "latin",
        "subs": [
            ("Salsa",               ["salsa"]),
            ("Bossa Nova",          ["bossa nova"]),
            ("Latin Pop",           ["latin pop"]),
            ("Reggaeton",           ["reggaeton"]),
            ("Flamenco",            ["flamenco"]),
            ("Cumbia",              ["cumbia"]),
            ("Merengue",            ["merengue"]),
            ("Tejano",              ["tejano"]),
        ],
    }),
    ("World", {
        "tag": "world music",
        "subs": [
            ("Afrobeat",            ["afrobeat"]),
            ("Celtic",              ["celtic"]),
            ("Middle Eastern",      ["arabic", "middle eastern"]),
            ("Indian Classical",    ["indian classical"]),
            ("Gypsy Jazz",          ["gypsy jazz"]),
            ("African",             ["african"]),
            ("Asian",               ["asian"]),
            ("Fado",                ["fado"]),
        ],
    }),
    ("Experimental", {
        "tag": "experimental",
        "subs": [
            ("Avant-Garde",         ["avant-garde"]),
            ("Noise Rock",          ["noise rock"]),
            ("Drone",               ["drone"]),
            ("Krautrock",           ["krautrock"]),
            ("Math Rock",           ["math rock"]),
            ("Musique Concrète",    ["musique concrete"]),
            ("Free Improvisation",  ["free improvisation"]),
        ],
    }),
])


def annotate_with_library(library_genres):
    """Return taxonomy as a list annotated with library match info."""
    lib = {g.lower() for g in library_genres}
    result = []
    for cat_name, cat_data in TAXONOMY.items():
        cat_match = cat_data['tag'] in lib
        annotated_subs = []
        for sub_name, sub_tags in cat_data['subs']:
            in_lib = any(t in lib for t in sub_tags)
            if in_lib:
                cat_match = True
            annotated_subs.append({
                'name':       sub_name,
                'tag':        sub_tags[0],
                'in_library': in_lib,
            })
        result.append({
            'name':       cat_name,
            'tag':        cat_data['tag'],
            'in_library': cat_match,
            'subs':       annotated_subs,
        })
    return result
