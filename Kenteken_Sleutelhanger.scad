// =============================================================================
// Nederlands Kenteken Sleutelhanger / Dutch License Plate Keychain
// =============================================================================
// MakerWorld Parametric Model Maker compatible OpenSCAD model.
// Geoptimaliseerd voor FDM 3D-printers (Bambu Lab AMS / multi-color):
// - Zwarte drager met zwarte buitenrand alléén rondom de hele plaat.
// - Blauw Europees vlak links waarvan de linkerhoeken meebuigen met de afgeronde buitenrand.
// - Sleutelgat op de plek van de EU-sterrencirkel (bovenin het blauwe vlak),
//   omringd door een witte ring.
// - Witte 'NL' landcode onder het sleutelgat in het blauwe vlak.
// - Zwart ingelegde kentekentekst in het gele vlak (met authentiek Nederlands kentekenfont).
// - Volledig vlakke toplaag (flush / erin) – perfect voor Textured PEI prints!

/* [Onderdeel Selectie] */
// Welk onderdeel weergeven/exporteren ("all" voor het complete model)
part = "all"; // [all:Alles (Preview), black:Alleen Zwart (Basis en letters), yellow:Alleen Geel (Nummerplaat), blue:Alleen Blauw (EU vlak), white:Alleen Wit (NL code)]

/* [Kenteken Instellingen] */
// Het gewenste kenteken (bijv. 12-AB-34, 1-ABC-23, AA-12-BB)
kenteken_tekst = "G-363-GZ";

// Lettertype voor kenteken ("Kenteken" is het officiële Nederlandse kentekenfont)
lettertype = "Kenteken"; // font

// Landcode onder het sleutelgat (standaard NL)
landcode = "NL";

// Lettergrootte van de landcode (NL) in mm
landcode_grootte = 3.2; // [1.8:0.2:4.5]

// Hoogte/grootte van de kentekentekst in mm
tekst_grootte = 7.8; // [6.0:0.2:10.0]

// Extra lijndikte / bold-effect voor de kentekentekst in mm
tekst_extra_dikte = 0.20; // [0.0:0.05:0.5]

/* [Afmetingen] */
// Totale lengte van de nummerplaat in mm
plaat_lengte = 71; // [50:1:110]

// Totale hoogte van de nummerplaat in mm
plaat_hoogte = 15; // [12:1:30]

// Totale dikte van de sleutelhanger in mm
totale_dikte = 3.0; // [2.0:0.2:5.0]

// Breedte van de zwarte buitenrand in mm
rand_breedte = 0.9; // [0.6:0.1:2.0]

// Hoekradius van de plaat in mm
hoek_radius = 2.0; // [1.0:0.5:4.0]

// Binnendiameter van het sleutelring-gat in mm
gat_diameter = 4.0; // [3.0:0.5:5.0]

// Breedte van de witte ring rondom het sleutelgat in mm (0 = geen ring, blauw loopt massief door tot aan het gat)
witte_ring_dikte = 0.0; // [0.0:0.1:1.5]

// Breedte van het blauwe EU-vlak in mm
eu_breedte = 9.2; // [7.0:0.2:15.0]

// Diepte van het gele en blauwe basisvlak in mm (vanaf onderkant opdruk naar beneden)
vlak_dikte = 0.6; // [0.4:0.2:1.2]

// Dikte van de bovenop liggende letters, witte NL en buitenrand in mm
opdruk_dikte = 0.6; // [0.4:0.2:1.0]

/* [Kleuren (Bambu Lab AMS / Multi-Color)] */
// Kleur van de zwarte houder, buitenrand en letters (Zwart)
kleur_zwart = "#111111"; // color

// Kleur van de kentekenplaat (Nederlands geel)
kleur_geel = "#FFCC00"; // color

// Kleur van het Europese vlak (EU blauw)
kleur_blauw = "#003399"; // color

// Kleur van de witte ring en NL landcode (Wit)
kleur_wit = "#FFFFFF"; // color

/* [Verborgen Parameters] */
/* [Hidden] */
$fn = 60;

// Positie van het sleutelgat: exact op de plek van de EU-sterrencirkel (bovenaan in het blauwe vlak)
gat_x = rand_breedte + (eu_breedte - rand_breedte) / 2;
gat_y = plaat_hoogte - rand_breedte - witte_ring_dikte - gat_diameter / 2 - 0.7;

// 2D buitencontour van de hele plaat
module plate_contour_2d() {
    hull() {
        translate([hoek_radius, hoek_radius]) circle(r=hoek_radius);
        translate([plaat_lengte - hoek_radius, hoek_radius]) circle(r=hoek_radius);
        translate([plaat_lengte - hoek_radius, plaat_hoogte - hoek_radius]) circle(r=hoek_radius);
        translate([hoek_radius, plaat_hoogte - hoek_radius]) circle(r=hoek_radius);
    }
}

// 2D binnenoppervlak (binnen de zwarte buitenrand)
module inner_plate_2d() {
    offset(r=-rand_breedte)
        plate_contour_2d();
}

// 2D blauw EU-vlak (buigt links mee met de afgeronde buitenrand)
module eu_field_2d() {
    intersection() {
        inner_plate_2d();
        square([eu_breedte, plaat_hoogte]);
    }
}

// 2D witte ring rondom het sleutelgat
module white_ring_2d() {
    difference() {
        translate([gat_x, gat_y])
            circle(d=gat_diameter + 2 * witte_ring_dikte);
        translate([gat_x, gat_y])
            circle(d=gat_diameter);
    }
}

// 2D witte landcode tekst (NL) onder het sleutelgat (instelbare grootte via Customizer)
module eu_country_text_2d() {
    let(
        y_pos = rand_breedte + 0.6
    ) {
        translate([gat_x, y_pos])
            text(
                landcode, 
                size=landcode_grootte, 
                font=lettertype, 
                halign="center", 
                valign="baseline"
            );
    }
}

// 2D zwarte letters en cijfers van het kenteken (gecentreerd en met instelbare grootte & lijndikte)
module plate_text_2d() {
    let(
        yellow_min_x = eu_breedte,
        yellow_max_x = plaat_lengte - rand_breedte,
        center_x = (yellow_min_x + yellow_max_x) / 2,
        center_y = plaat_hoogte / 2
    ) {
        translate([center_x, center_y]) {
            if (tekst_extra_dikte > 0) {
                offset(delta=tekst_extra_dikte)
                    text(
                        text=kenteken_tekst, 
                        size=tekst_grootte, 
                        font=lettertype, 
                        halign="center", 
                        valign="center"
                    );
            } else {
                text(
                    text=kenteken_tekst, 
                    size=tekst_grootte, 
                    font=lettertype, 
                    halign="center", 
                    valign="center"
                );
            }
        }
    }
}

// =============================================================================
// 3D Modules (Gelaagd / Economisch Multi-Color)
// =============================================================================
// Laagopbouw:
// Z = 0.0 tot Z = z_bodem : Zwarte massieve basis/drager
// Z = z_bodem tot Z = z_vlak : Blauw en Geel vlak (zonder filamentwissels met wit/zwart!)
// Z = z_vlak tot Z = totale_dikte : Zwarte rand + zwarte letters + witte NL bovenop

z_bodem = totale_dikte - vlak_dikte - opdruk_dikte;
z_vlak = totale_dikte - opdruk_dikte;

// 1. Zwart: Massieve achterkant/drager + verhoogde buitenrand + verhoogde letters
module BlackParts() {
    color(kleur_zwart) {
        // Onderste massieve laag (bodem van de sleutelhanger)
        linear_extrude(height=z_bodem)
            difference() {
                plate_contour_2d();
                translate([gat_x, gat_y]) circle(d=gat_diameter);
            }
            
        // Bovenste laag (op z = z_vlak): Zwarte buitenrand + zwarte kentekentekst bovenop het geel
        translate([0, 0, z_vlak])
            linear_extrude(height=opdruk_dikte) {
                // Zwarte buitenrand om de gehele plaat
                difference() {
                    plate_contour_2d();
                    inner_plate_2d();
                }
                // Kentekentekst verhoogd / bovenop het gele vlak
                plate_text_2d();
            }
    }
}

// 2. Geel: Massief nummerplaat vlak (volledig onder de letters doorlopend, geen uitsnijdingen!)
module YellowPart() {
    color(kleur_geel)
    translate([0, 0, z_bodem])
        linear_extrude(height=vlak_dikte)
            difference() {
                inner_plate_2d();
                eu_field_2d();
            }
}

// 3. Blauw: Massief Europees vlak aan de linkerzijde (volledig onder de witte tekst doorlopend!)
module BluePart() {
    color(kleur_blauw)
    translate([0, 0, z_bodem])
        linear_extrude(height=vlak_dikte)
            difference() {
                eu_field_2d();
                // Uitsparing voor het gat (plus ring indien ingesteld)
                translate([gat_x, gat_y])
                    circle(d=gat_diameter + (witte_ring_dikte > 0 ? 2 * witte_ring_dikte : 0));
            }
}

// 4. Wit: Bovenop liggende witte NL landcode (+ optionele ring rondom sleutelgat)
module WhiteParts() {
    color(kleur_wit)
    translate([0, 0, z_vlak])
        linear_extrude(height=opdruk_dikte) {
            if (witte_ring_dikte > 0) {
                white_ring_2d();
            }
            eu_country_text_2d();
        }
}

// =============================================================================
// Samenstelling op basis van part parameter
// =============================================================================
if (part == "all") {
    BlackParts();
    YellowPart();
    BluePart();
    WhiteParts();
} else if (part == "black") {
    BlackParts();
} else if (part == "yellow") {
    YellowPart();
} else if (part == "blue") {
    BluePart();
} else if (part == "white") {
    WhiteParts();
}
