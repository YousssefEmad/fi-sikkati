import type { SuggestOption } from "@/lib/suggest";

interface Model {
  id: string;
  ar: string;
  en: string;
}
interface Make {
  id: string;
  ar: string;
  en: string;
  models: readonly Model[];
}

const MAKES: readonly Make[] = [
  { id: "toyota", ar: "تويوتا", en: "Toyota", models: models(["corolla", "كورولا", "Corolla"], ["yaris", "يارس", "Yaris"], ["hilux", "هايلكس", "Hilux"], ["fortuner", "فورتشنر", "Fortuner"], ["land-cruiser", "لاند كروزر", "Land Cruiser"], ["camry", "كامري", "Camry"], ["corolla-cross", "كورولا كروس", "Corolla Cross"]) },
  { id: "hyundai", ar: "هيونداي", en: "Hyundai", models: models(["elantra", "إلنترا", "Elantra"], ["accent", "أكسنت", "Accent"], ["tucson", "توسان", "Tucson"], ["creta", "كريتا", "Creta"], ["verna", "فيرنا", "Verna"], ["i10", "i10", "i10"], ["i20", "i20", "i20"], ["santa-fe", "سانتا في", "Santa Fe"]) },
  { id: "nissan", ar: "نيسان", en: "Nissan", models: models(["sunny", "صني", "Sunny"], ["sentra", "سنترا", "Sentra"], ["qashqai", "قشقاي", "Qashqai"], ["juke", "جوك", "Juke"], ["patrol", "باترول", "Patrol"], ["kicks", "كيكس", "Kicks"]) },
  { id: "kia", ar: "كيا", en: "Kia", models: models(["cerato", "سيراتو", "Cerato"], ["sportage", "سبورتاج", "Sportage"], ["picanto", "بيكانتو", "Picanto"], ["rio", "ريو", "Rio"], ["seltos", "سيلتوس", "Seltos"], ["carnival", "كرنفال", "Carnival"]) },
  { id: "chevrolet", ar: "شيفروليه", en: "Chevrolet", models: models(["optra", "أوبترا", "Optra"], ["aveo", "أفيو", "Aveo"], ["cruze", "كروز", "Cruze"], ["captiva", "كابتيفا", "Captiva"], ["lanos", "لانوس", "Lanos"], ["n300", "N300", "N300"]) },
  { id: "mitsubishi", ar: "ميتسوبيشي", en: "Mitsubishi", models: models(["lancer", "لانسر", "Lancer"], ["pajero", "باجيرو", "Pajero"], ["xpander", "إكسباندر", "Xpander"], ["attrage", "أتراج", "Attrage"], ["l200", "L200", "L200"]) },
  { id: "suzuki", ar: "سوزوكي", en: "Suzuki", models: models(["swift", "سويفت", "Swift"], ["dzire", "ديزاير", "Dzire"], ["ciaz", "سياز", "Ciaz"], ["vitara", "فيتارا", "Vitara"], ["alto", "ألتو", "Alto"], ["ertiga", "إرتيجا", "Ertiga"]) },
  { id: "renault", ar: "رينو", en: "Renault", models: models(["logan", "لوجان", "Logan"], ["megane", "ميجان", "Megane"], ["duster", "داستر", "Duster"], ["sandero", "سانديرو", "Sandero"], ["stepway", "ستيبواي", "Stepway"]) },
  { id: "peugeot", ar: "بيجو", en: "Peugeot", models: models(["301", "301", "301"], ["508", "508", "508"], ["3008", "3008", "3008"], ["2008", "2008", "2008"]) },
  { id: "fiat", ar: "فيات", en: "Fiat", models: models(["tipo", "تيبو", "Tipo"], ["punto", "بونتو", "Punto"], ["500", "500", "500"]) },
  { id: "skoda", ar: "سكودا", en: "Skoda", models: models(["octavia", "أوكتافيا", "Octavia"], ["fabia", "فابيا", "Fabia"], ["kodiaq", "كودياك", "Kodiaq"], ["superb", "سوبيرب", "Superb"]) },
  { id: "volkswagen", ar: "فولكس فاجن", en: "Volkswagen", models: models(["golf", "جولف", "Golf"], ["passat", "باسات", "Passat"], ["tiguan", "تيجوان", "Tiguan"], ["polo", "بولو", "Polo"]) },
  { id: "bmw", ar: "بي إم دبليو", en: "BMW", models: models(["3", "الفئة الثالثة", "3 Series"], ["5", "الفئة الخامسة", "5 Series"], ["x1", "X1", "X1"], ["x3", "X3", "X3"], ["x5", "X5", "X5"]) },
  { id: "mercedes", ar: "مرسيدس", en: "Mercedes-Benz", models: models(["c", "C-Class", "C-Class"], ["e", "E-Class", "E-Class"], ["gla", "GLA", "GLA"], ["glc", "GLC", "GLC"]) },
  { id: "honda", ar: "هوندا", en: "Honda", models: models(["civic", "سيفيك", "Civic"], ["city", "سيتي", "City"], ["accord", "أكورد", "Accord"], ["crv", "CR-V", "CR-V"]) },
  { id: "mg", ar: "إم جي", en: "MG", models: models(["mg5", "MG 5", "MG 5"], ["zs", "ZS", "ZS"], ["hs", "HS", "HS"], ["rx5", "RX5", "RX5"]) },
  { id: "chery", ar: "شيري", en: "Chery", models: models(["tiggo7", "تيجو 7", "Tiggo 7"], ["tiggo4", "تيجو 4", "Tiggo 4"], ["arrizo", "أريزو", "Arrizo"]) },
  { id: "geely", ar: "جيلي", en: "Geely", models: models(["emgrand", "إمجراند", "Emgrand"], ["coolray", "كولراي", "Coolray"]) },
  { id: "byd", ar: "بي واي دي", en: "BYD", models: models(["f3", "F3", "F3"], ["atto3", "أتو 3", "Atto 3"], ["seal", "سيل", "Seal"]) },
  { id: "opel", ar: "أوبل", en: "Opel", models: models(["astra", "أسترا", "Astra"], ["corsa", "كورسا", "Corsa"], ["crossland", "كروسلاند", "Crossland"]) },
  { id: "ford", ar: "فورد", en: "Ford", models: models(["focus", "فوكاس", "Focus"], ["fiesta", "فيستا", "Fiesta"], ["ecosport", "إيكو سبورت", "EcoSport"]) },
  { id: "jeep", ar: "جيب", en: "Jeep", models: models(["cherokee", "شيروكي", "Cherokee"], ["wrangler", "رانجلر", "Wrangler"]) },
  { id: "mazda", ar: "مازدا", en: "Mazda", models: models(["mazda3", "مازدا 3", "Mazda 3"], ["cx5", "CX-5", "CX-5"]) },
  { id: "audi", ar: "أودي", en: "Audi", models: models(["a3", "A3", "A3"], ["a4", "A4", "A4"], ["q5", "Q5", "Q5"]) },
  { id: "speranza", ar: "سبيرانزا", en: "Speranza", models: models(["a516", "A516", "A516"], ["a113", "A113", "A113"]) },
  { id: "lada", ar: "لادا", en: "Lada", models: models(["granta", "جرانتا", "Granta"]) },
];

const COLORS: readonly { id: string; ar: string; en: string }[] = [
  { id: "white", ar: "أبيض", en: "White" },
  { id: "black", ar: "أسود", en: "Black" },
  { id: "silver", ar: "فضي", en: "Silver" },
  { id: "grey", ar: "رمادي", en: "Grey" },
  { id: "blue", ar: "أزرق", en: "Blue" },
  { id: "navy", ar: "كحلي", en: "Navy" },
  { id: "red", ar: "أحمر", en: "Red" },
  { id: "beige", ar: "بيج", en: "Beige" },
  { id: "brown", ar: "بني", en: "Brown" },
  { id: "green", ar: "أخضر", en: "Green" },
  { id: "gold", ar: "ذهبي", en: "Gold" },
];

function models(...rows: readonly (readonly [string, string, string])[]): Model[] {
  return rows.map(([id, ar, en]) => ({ id, ar, en }));
}

function asOption(locale: string, row: { id: string; ar: string; en: string }, pinned = true): SuggestOption {
  const arabic = locale.startsWith("ar");
  return {
    id: row.id,
    label: arabic ? row.ar : row.en,
    keywords: `${row.ar} ${row.en}`,
    pinned,
  };
}

export function makeOptions(locale: string): SuggestOption[] {
  return MAKES.map((make) => asOption(locale, make));
}

export function modelOptions(locale: string, makeId: string | null): SuggestOption[] {
  const makes = makeId ? MAKES.filter((make) => make.id === makeId) : MAKES;
  return makes.flatMap((make) =>
    make.models.map((model) => ({
      ...asOption(locale, model),
      id: `${make.id}:${model.id}`,
      hint: locale.startsWith("ar") ? make.ar : make.en,
    })),
  );
}

export function colorOptions(locale: string): SuggestOption[] {
  return COLORS.map((color) => asOption(locale, color));
}

export function yearOptions(from = 1998, to = new Date().getFullYear() + 1): SuggestOption[] {
  const years: SuggestOption[] = [];
  for (let year = to; year >= from; year -= 1) {
    years.push({ id: String(year), label: String(year), pinned: year >= to - 12 });
  }
  return years;
}

export function seatOptions(max = 8): SuggestOption[] {
  return Array.from({ length: max }, (_, index) => {
    const seats = String(index + 1);
    return { id: seats, label: seats, pinned: true };
  });
}
