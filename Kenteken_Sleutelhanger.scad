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

/* [Kenteken Instellingen] */
// Het gewenste kenteken (bijv. 12-AB-34, 1-ABC-23, AA-12-BB)
kenteken_tekst = "AA-12-BB";

// Lettertype voor kenteken ("Kenteken" is het officiële Nederlandse kentekenfont)
lettertype = "Kenteken"; // font

// Landcode onder het sleutelgat (standaard NL)
landcode = "NL";

// Lettergrootte van de landcode (NL) in mm
landcode_grootte = 3.2; // [1.8:0.2:4.5]

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
gat_diameter = 3.5; // [2.5:0.5:5.0]

// Breedte van de witte beschermring rondom het sleutelgat in mm
witte_ring_dikte = 0.8; // [0.5:0.1:1.5]

// Breedte van het blauwe EU-vlak in mm
eu_breedte = 9.2; // [7.0:0.2:15.0]

// Diepte van de kleur-inleg in mm (vanaf de toplaag naar beneden)
inleg_diepte = 0.6; // [0.4:0.2:1.2]

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

// 2D zwarte letters en cijfers van het kenteken (horizontaal en verticaal gecentreerd)
module plate_text_2d() {
    let(
        yellow_min_x = eu_breedte,
        yellow_max_x = plaat_lengte - rand_breedte,
        center_x = (yellow_min_x + yellow_max_x) / 2,
        center_y = plaat_hoogte / 2,
        font_size = plaat_hoogte * 0.48
    ) {
        translate([center_x, center_y])
            text(
                text=kenteken_tekst, 
                size=font_size, 
                font=lettertype, 
                halign="center", 
                valign="center"
            );
    }
}

// =============================================================================
// 3D Modules (Per Kleur)
// =============================================================================

// 1. Zwart: Massieve achterkant/drager + buitenrand alléén om de hele plaat + letters
module BlackParts() {
    color(kleur_zwart) {
        // Onderste massieve laag (bodem van de sleutelhanger)
        linear_extrude(height=totale_dikte - inleg_diepte)
            difference() {
                plate_contour_2d();
                translate([gat_x, gat_y]) circle(d=gat_diameter);
            }
            
        // Bovenste laag: Zwarte buitenrand om de héle plaat + zwarte kentekentekst
        translate([0, 0, totale_dikte - inleg_diepte])
            linear_extrude(height=inleg_diepte) {
                // Alleen de zwarte buitenrand om de gehele plaat
                difference() {
                    plate_contour_2d();
                    inner_plate_2d();
                }
                // Kentekentekst ingelegd
                plate_text_2d();
            }
    }
}

// 2. Geel: Nummerplaat achtergrond
module YellowPart() {
    color(kleur_geel)
    translate([0, 0, totale_dikte - inleg_diepte])
        linear_extrude(height=inleg_diepte)
            difference() {
                inner_plate_2d();
                eu_field_2d();
                plate_text_2d();
            }
}

// 3. Blauw: Europees vlak aan de linkerzijde
module BluePart() {
    color(kleur_blauw)
    translate([0, 0, totale_dikte - inleg_diepte])
        linear_extrude(height=inleg_diepte)
            difference() {
                eu_field_2d();
                // Uitsparing voor het sleutelgat en de witte beschermring
                translate([gat_x, gat_y])
                    circle(d=gat_diameter + 2 * witte_ring_dikte);
                // Uitsparing voor de witte NL landcode
                eu_country_text_2d();
            }
}

// 4. Wit: Ring rondom het sleutelgat + NL landcode
module WhiteParts() {
    color(kleur_wit)
    translate([0, 0, totale_dikte - inleg_diepte])
        linear_extrude(height=inleg_diepte) {
            white_ring_2d();
            eu_country_text_2d();
        }
}

// =============================================================================
// Volledige Samenstelling (Alles sluit naadloos aan op z = totale_dikte)
// =============================================================================
BlackParts();
YellowPart();
BluePart();
WhiteParts();
