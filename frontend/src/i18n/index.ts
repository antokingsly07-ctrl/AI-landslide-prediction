import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en";
import hi from "./hi";
import as from "./as";
import bn from "./bn";
import ta from "./ta";

export const resources = {
  en: { translation: en },
  hi: { translation: hi },
  as: { translation: as },
  bn: { translation: bn },
  ta: { translation: ta },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
