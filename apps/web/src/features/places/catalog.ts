import type { SuggestOption } from "@/lib/suggest";

type Governorate = "cairo" | "giza" | "qalyubia";

interface Place {
  id: string;
  ar: string;
  en: string;
  lat: number;
  lng: number;
  gov: Governorate;
  pinned?: boolean;
}

const GOVERNORATE: Record<Governorate, { ar: string; en: string }> = {
  cairo: { ar: "القاهرة", en: "Cairo" },
  giza: { ar: "الجيزة", en: "Giza" },
  qalyubia: { ar: "القليوبية", en: "Qalyubia" },
};

/**
 * Cities and districts of Greater Cairo. Coordinates are area centroids (WGS84),
 * accurate enough to match a shared ride, not a street address.
 */
const PLACES: readonly Place[] = [
  { id: "cairo", ar: "القاهرة", en: "Cairo", lat: 30.0444, lng: 31.2357, gov: "cairo", pinned: true },
  { id: "giza", ar: "الجيزة", en: "Giza", lat: 30.0131, lng: 31.2089, gov: "giza", pinned: true },
  { id: "obour", ar: "مدينة العبور", en: "El Obour", lat: 30.1935, lng: 31.4694, gov: "qalyubia", pinned: true },
  { id: "nasr", ar: "مدينة نصر", en: "Nasr City", lat: 30.0561, lng: 31.33, gov: "cairo", pinned: true },
  { id: "heliopolis", ar: "مصر الجديدة", en: "Heliopolis", lat: 30.0875, lng: 31.3242, gov: "cairo", pinned: true },
  { id: "new-cairo", ar: "القاهرة الجديدة", en: "New Cairo", lat: 30.03, lng: 31.47, gov: "cairo", pinned: true },
  { id: "fifth", ar: "التجمع الخامس", en: "Fifth Settlement", lat: 30.0074, lng: 31.4433, gov: "cairo", pinned: true },
  { id: "rehab", ar: "الرحاب", en: "Rehab", lat: 30.06, lng: 31.49, gov: "cairo", pinned: true },
  { id: "madinaty", ar: "مدينتي", en: "Madinaty", lat: 30.0752, lng: 31.6374, gov: "cairo", pinned: true },
  { id: "shorouk", ar: "الشروق", en: "El Shorouk", lat: 30.1186, lng: 31.605, gov: "cairo", pinned: true },
  { id: "badr", ar: "بدر", en: "Badr", lat: 30.136, lng: 31.715, gov: "cairo", pinned: true },
  { id: "new-capital", ar: "العاصمة الإدارية", en: "New Administrative Capital", lat: 30.02, lng: 31.75, gov: "cairo", pinned: true },
  { id: "maadi", ar: "المعادي", en: "Maadi", lat: 29.96, lng: 31.25, gov: "cairo", pinned: true },
  { id: "helwan", ar: "حلوان", en: "Helwan", lat: 29.841, lng: 31.3, gov: "cairo", pinned: true },
  { id: "october", ar: "6 أكتوبر", en: "6th of October", lat: 29.9285, lng: 30.9188, gov: "giza", pinned: true },
  { id: "zayed", ar: "الشيخ زايد", en: "Sheikh Zayed", lat: 30.02, lng: 30.98, gov: "giza", pinned: true },
  { id: "downtown", ar: "وسط البلد", en: "Downtown", lat: 30.0444, lng: 31.2357, gov: "cairo", pinned: true },
  { id: "zamalek", ar: "الزمالك", en: "Zamalek", lat: 30.0609, lng: 31.2196, gov: "cairo", pinned: true },
  { id: "mohandessin", ar: "المهندسين", en: "Mohandessin", lat: 30.053, lng: 31.2, gov: "giza", pinned: true },
  { id: "dokki", ar: "الدقي", en: "Dokki", lat: 30.038, lng: 31.212, gov: "giza", pinned: true },
  { id: "haram", ar: "الهرم", en: "Haram", lat: 29.99, lng: 31.15, gov: "giza", pinned: true },
  { id: "faisal", ar: "فيصل", en: "Faisal", lat: 30.017, lng: 31.175, gov: "giza", pinned: true },
  { id: "shubra-el-kheima", ar: "شبرا الخيمة", en: "Shubra El Kheima", lat: 30.122, lng: 31.244, gov: "qalyubia", pinned: true },
  { id: "hadayek-ahram", ar: "حدائق الأهرام", en: "Hadayek Al Ahram", lat: 29.98, lng: 31.1, gov: "giza", pinned: true },

  { id: "obour-industrial", ar: "المنطقة الصناعية بالعبور", en: "El Obour Industrial Zone", lat: 30.215, lng: 31.455, gov: "qalyubia" },
  { id: "obour-1", ar: "الحي الأول — العبور", en: "El Obour District 1", lat: 30.23, lng: 31.48, gov: "qalyubia" },
  { id: "obour-9", ar: "الحي التاسع — العبور", en: "El Obour District 9", lat: 30.18, lng: 31.46, gov: "qalyubia" },
  { id: "ramses", ar: "رمسيس", en: "Ramses", lat: 30.0626, lng: 31.247, gov: "cairo" },
  { id: "garden", ar: "جاردن سيتي", en: "Garden City", lat: 30.0355, lng: 31.2305, gov: "cairo" },
  { id: "shubra", ar: "شبرا", en: "Shubra", lat: 30.0765, lng: 31.244, gov: "cairo" },
  { id: "rod-el-farag", ar: "روض الفرج", en: "Rod El Farag", lat: 30.08, lng: 31.23, gov: "cairo" },
  { id: "sahel", ar: "الساحل", en: "El Sahel", lat: 30.085, lng: 31.245, gov: "cairo" },
  { id: "hadayek-kobba", ar: "حدائق القبة", en: "Hadayek El Kobba", lat: 30.095, lng: 31.28, gov: "cairo" },
  { id: "zaytoun", ar: "الزيتون", en: "El Zaytoun", lat: 30.113, lng: 31.31, gov: "cairo" },
  { id: "ain-shams", ar: "عين شمس", en: "Ain Shams", lat: 30.128, lng: 31.33, gov: "cairo" },
  { id: "matariya", ar: "المطرية", en: "El Matariya", lat: 30.128, lng: 31.305, gov: "cairo" },
  { id: "marg", ar: "المرج", en: "El Marg", lat: 30.152, lng: 31.34, gov: "cairo" },
  { id: "salam", ar: "السلام", en: "El Salam", lat: 30.17, lng: 31.41, gov: "cairo" },
  { id: "nozha", ar: "النزهة", en: "El Nozha", lat: 30.1, lng: 31.34, gov: "cairo" },
  { id: "korba", ar: "الكوربة", en: "Korba", lat: 30.087, lng: 31.322, gov: "cairo" },
  { id: "abbassia", ar: "العباسية", en: "Abbassia", lat: 30.072, lng: 31.275, gov: "cairo" },
  { id: "zaher", ar: "الظاهر", en: "El Zaher", lat: 30.062, lng: 31.265, gov: "cairo" },
  { id: "sayeda", ar: "السيدة زينب", en: "Sayeda Zeinab", lat: 30.03, lng: 31.235, gov: "cairo" },
  { id: "old-cairo", ar: "مصر القديمة", en: "Old Cairo", lat: 30.01, lng: 31.23, gov: "cairo" },
  { id: "fustat", ar: "الفسطاط", en: "Fustat", lat: 30.006, lng: 31.231, gov: "cairo" },
  { id: "new-maadi", ar: "المعادي الجديدة", en: "New Maadi", lat: 29.97, lng: 31.3, gov: "cairo" },
  { id: "dar-el-salam", ar: "دار السلام", en: "Dar El Salam", lat: 29.98, lng: 31.24, gov: "cairo" },
  { id: "basatin", ar: "البساتين", en: "El Basatin", lat: 29.995, lng: 31.265, gov: "cairo" },
  { id: "tora", ar: "طرة", en: "Tora", lat: 29.94, lng: 31.28, gov: "cairo" },
  { id: "15-may", ar: "15 مايو", en: "15th of May", lat: 29.83, lng: 31.37, gov: "cairo" },
  { id: "mokattam", ar: "المقطم", en: "Mokattam", lat: 30.01, lng: 31.3, gov: "cairo" },
  { id: "zawya", ar: "الزاوية الحمراء", en: "El Zawya El Hamra", lat: 30.065, lng: 31.26, gov: "cairo" },
  { id: "sharabiya", ar: "الشرابية", en: "El Sharabiya", lat: 30.09, lng: 31.255, gov: "cairo" },
  { id: "manshiyet-nasser", ar: "منشية ناصر", en: "Manshiyat Nasser", lat: 30.04, lng: 31.275, gov: "cairo" },
  { id: "first-settlement", ar: "التجمع الأول", en: "First Settlement", lat: 30.05, lng: 31.45, gov: "cairo" },
  { id: "third-settlement", ar: "التجمع الثالث", en: "Third Settlement", lat: 30.02, lng: 31.49, gov: "cairo" },
  { id: "katameya", ar: "القطامية", en: "Katameya", lat: 29.99, lng: 31.4, gov: "cairo" },
  { id: "festival", ar: "كايرو فستيفال سيتي", en: "Cairo Festival City", lat: 30.0278, lng: 31.4075, gov: "cairo" },
  { id: "mostakbal", ar: "المستقبل سيتي", en: "Mostakbal City", lat: 30.11, lng: 31.65, gov: "cairo" },

  { id: "agouza", ar: "العجوزة", en: "Agouza", lat: 30.055, lng: 31.21, gov: "giza" },
  { id: "talbiya", ar: "الطالبية", en: "Talbiya", lat: 29.995, lng: 31.18, gov: "giza" },
  { id: "omraniya", ar: "العمرانية", en: "Omraniya", lat: 30, lng: 31.19, gov: "giza" },
  { id: "imbaba", ar: "إمبابة", en: "Imbaba", lat: 30.075, lng: 31.205, gov: "giza" },
  { id: "warraq", ar: "الوراق", en: "El Warraq", lat: 30.1, lng: 31.2, gov: "giza" },
  { id: "boulaq", ar: "بولاق الدكرور", en: "Boulaq El Dakrour", lat: 30.035, lng: 31.19, gov: "giza" },
  { id: "kitkat", ar: "الكيت كات", en: "Kit Kat", lat: 30.065, lng: 31.21, gov: "giza" },
  { id: "ard-ellewa", ar: "أرض اللواء", en: "Ard El Lewa", lat: 30.08, lng: 31.195, gov: "giza" },
  { id: "moneeb", ar: "المنيب", en: "El Moneeb", lat: 29.98, lng: 31.21, gov: "giza" },
  { id: "abu-nomros", ar: "أبو النمرس", en: "Abu Nomros", lat: 29.95, lng: 31.2, gov: "giza" },
  { id: "hawamdiya", ar: "الحوامدية", en: "Hawamdiya", lat: 29.9, lng: 31.25, gov: "giza" },
  { id: "october-heights", ar: "حدائق أكتوبر", en: "Hadayek October", lat: 29.9, lng: 30.95, gov: "giza" },
  { id: "dreamland", ar: "دريم لاند", en: "Dreamland", lat: 30, lng: 30.97, gov: "giza" },
  { id: "motamayez", ar: "الحي المتميز", en: "El Motamayez District", lat: 29.97, lng: 30.95, gov: "giza" },

  { id: "qalyub", ar: "قليوب", en: "Qalyub", lat: 30.179, lng: 31.205, gov: "qalyubia" },
  { id: "qanater", ar: "القناطر الخيرية", en: "El Qanater El Khayreya", lat: 30.195, lng: 31.14, gov: "qalyubia" },
  { id: "khanka", ar: "الخانكة", en: "El Khanka", lat: 30.21, lng: 31.368, gov: "qalyubia" },
  { id: "banha", ar: "بنها", en: "Banha", lat: 30.466, lng: 31.184, gov: "qalyubia" },
  { id: "khosous", ar: "الخصوص", en: "El Khosous", lat: 30.155, lng: 31.31, gov: "qalyubia" },
  { id: "abu-zaabal", ar: "أبو زعبل", en: "Abu Zaabal", lat: 30.24, lng: 31.4, gov: "qalyubia" },
  { id: "bahtim", ar: "بهتيم", en: "Bahtim", lat: 30.13, lng: 31.26, gov: "qalyubia" },
  { id: "mostorod", ar: "مسطرد", en: "Mostorod", lat: 30.14, lng: 31.29, gov: "qalyubia" },
];

export interface PlaceOption extends SuggestOption {
  lat: number;
  lng: number;
}

export function placesFor(locale: string): PlaceOption[] {
  const arabic = locale.startsWith("ar");
  return PLACES.map((place) => ({
    id: place.id,
    label: arabic ? place.ar : place.en,
    keywords: `${place.ar} ${place.en}`,
    hint: arabic ? GOVERNORATE[place.gov].ar : GOVERNORATE[place.gov].en,
    pinned: place.pinned === true,
    lat: place.lat,
    lng: place.lng,
  }));
}
