import mcq from "./mcq.js";
import matchByLine from "./match-by-line.js";
import categorize from "./categorize.js";
import translatePhrase from "./translate-phrase.js";
import transform from "./transform.js";
import paradigmTag from "./paradigm-tag.js";
import paradigmFill from "./paradigm-fill.js";
import multiTranslation from "./multi-translation.js";
import fillBlankVerse from "./fill-blank-verse.js";
import scanText from "./scan-text.js";
import synonymAntonym from "./synonym-antonym.js";
import dictation from "./dictation.js";
import rootPatternCompose from "./root-pattern-compose.js";
import spotError from "./spot-error.js";
import translitNormalize from "./translit-normalize.js";
import gapFillVerse from "./gap-fill-verse.js";
import flashTimed from "./flash-timed.js";
import identifyBinyan from "./identify-binyan.js";
import buildConstructChain from "./build-construct-chain.js";
import parseNoun from "./parse-noun.js";
import parseVerb from "./parse-verb.js";
import produceForm from "./produce-form.js";
import parseForm from "./parse-form.js";
import trueFalse from "./true-false.js";

const registry = new Map();

function register(plugin) {
  registry.set(plugin.id, plugin);
}

register(mcq);
register(matchByLine);
register(categorize);
register(translatePhrase);
register(transform);
register(paradigmTag);
register(paradigmFill);
register(multiTranslation);
register(fillBlankVerse);
register(scanText);
register(synonymAntonym);
register(dictation);
register(rootPatternCompose);
register(spotError);
register(translitNormalize);
register(gapFillVerse);
register(flashTimed);
register(identifyBinyan);
register(buildConstructChain);
register(parseNoun);
register(parseVerb);
register(parseForm);
register(trueFalse);
register(produceForm);

export function getType(id) {
  return registry.get(id);
}

export function typeIds() {
  return [...registry.keys()];
}
