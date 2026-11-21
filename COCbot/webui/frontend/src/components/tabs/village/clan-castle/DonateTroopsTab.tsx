import { useState } from "react";
import { Swords, Sparkles, Castle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";

interface UnitItem {
  id: string;
  name: string;
  short: string;
  defaultKeywords: string;
  category: "Troops" | "Spells" | "Siege";
}

const DONATE_UNITS: UnitItem[] = [
  { id: "barb", name: "Barbarians", short: "Barb", defaultKeywords: "barbarian\nbarbarians", category: "Troops" },
  { id: "arch", name: "Archers", short: "Arch", defaultKeywords: "archer\narchers", category: "Troops" },
  { id: "giant", name: "Giants", short: "Giant", defaultKeywords: "giant\ngiants", category: "Troops" },
  { id: "gob", name: "Goblins", short: "Gob", defaultKeywords: "goblin\ngoblins", category: "Troops" },
  { id: "wb", name: "Wall Breakers", short: "WB", defaultKeywords: "wall breaker\nwb", category: "Troops" },
  { id: "loon", name: "Balloons", short: "Loon", defaultKeywords: "balloon\nballoons\nloon", category: "Troops" },
  { id: "wiz", name: "Wizards", short: "Wiz", defaultKeywords: "wizard\nwizards\nwiz", category: "Troops" },
  { id: "heal", name: "Healers", short: "Heal", defaultKeywords: "healer\nhealers", category: "Troops" },
  { id: "drag", name: "Dragons", short: "Drag", defaultKeywords: "dragon\ndragons", category: "Troops" },
  { id: "pekka", name: "P.E.K.K.As", short: "Pekka", defaultKeywords: "pekka\np.e.k.k.a", category: "Troops" },
  { id: "bdrag", name: "Baby Dragons", short: "BDrag", defaultKeywords: "baby dragon\nbaby", category: "Troops" },
  { id: "miner", name: "Miners", short: "Miner", defaultKeywords: "miner\nminers", category: "Troops" },
  { id: "edrag", name: "Electro Dragons", short: "EDrag", defaultKeywords: "electro dragon\nedrag", category: "Troops" },
  { id: "yeti", name: "Yetis", short: "Yeti", defaultKeywords: "yeti\nyetis", category: "Troops" },
  { id: "drider", name: "Dragon Riders", short: "DRider", defaultKeywords: "dragon rider", category: "Troops" },
  { id: "etitan", name: "Electro Titans", short: "ETitan", defaultKeywords: "electro titan\ntitan", category: "Troops" },
  { id: "rrider", name: "Root Riders", short: "RRider", defaultKeywords: "root rider\nroot", category: "Troops" },
  { id: "thrower", name: "Throwers", short: "Throw", defaultKeywords: "thrower\nthrowers", category: "Troops" },
  { id: "minion", name: "Minions", short: "Minion", defaultKeywords: "minion\nminions", category: "Troops" },
  { id: "hog", name: "Hog Riders", short: "Hog", defaultKeywords: "hog rider\nhog", category: "Troops" },
  { id: "valk", name: "Valkyries", short: "Valk", defaultKeywords: "valkyrie\nvalk", category: "Troops" },
  { id: "golem", name: "Golems", short: "Golem", defaultKeywords: "golem\ngolems", category: "Troops" },
  { id: "witch", name: "Witches", short: "Witch", defaultKeywords: "witch\nwitches", category: "Troops" },
  { id: "hound", name: "Lava Hounds", short: "Hound", defaultKeywords: "lava hound\nhound", category: "Troops" },
  { id: "bowler", name: "Bowlers", short: "Bowler", defaultKeywords: "bowler\nbowlers", category: "Troops" },
  { id: "igolem", name: "Ice Golems", short: "IGolem", defaultKeywords: "ice golem\nice", category: "Troops" },
  { id: "hh", name: "Headhunters", short: "HH", defaultKeywords: "headhunter\nhh", category: "Troops" },
  { id: "awarden", name: "Apprentice Wardens", short: "AWard", defaultKeywords: "apprentice warden", category: "Troops" },
  { id: "druid", name: "Druids", short: "Druid", defaultKeywords: "druid\ndruids", category: "Troops" },
  { id: "furnace", name: "Furnaces", short: "Furn", defaultKeywords: "furnace", category: "Troops" },
  { id: "sbarb", name: "Super Barbarians", short: "SBarb", defaultKeywords: "super barbarian\nsbarb", category: "Troops" },
  { id: "sarch", name: "Super Archers", short: "SArch", defaultKeywords: "super archer\nsarch", category: "Troops" },
  { id: "sgob", name: "Sneaky Goblins", short: "Sneaky", defaultKeywords: "sneaky goblin\nsneaky", category: "Troops" },
  { id: "swb", name: "Super Wall Breakers", short: "SWB", defaultKeywords: "super wall breaker\nswb", category: "Troops" },
  { id: "rloon", name: "Rocket Balloons", short: "RLoon", defaultKeywords: "rocket balloon\nrocket", category: "Troops" },
  { id: "swiz", name: "Super Wizards", short: "SWiz", defaultKeywords: "super wizard\nswiz", category: "Troops" },
  { id: "sdrag", name: "Super Dragons", short: "SDrag", defaultKeywords: "super dragon\nsdrag", category: "Troops" },
  { id: "idrag", name: "Inferno Dragons", short: "IDrag", defaultKeywords: "inferno dragon\nidrag", category: "Troops" },
  { id: "smin", name: "Super Minions", short: "SMin", defaultKeywords: "super minion\nsmin", category: "Troops" },
  { id: "svalk", name: "Super Valkyries", short: "SValk", defaultKeywords: "super valkyrie", category: "Troops" },
  { id: "switch", name: "Super Witches", short: "SWitch", defaultKeywords: "super witch", category: "Troops" },
  { id: "ihound", name: "Ice Hounds", short: "IHound", defaultKeywords: "ice hound", category: "Troops" },
  { id: "sbowl", name: "Super Bowlers", short: "SBowl", defaultKeywords: "super bowler", category: "Troops" },
  { id: "sminer", name: "Super Miners", short: "SMiner", defaultKeywords: "super miner", category: "Troops" },
  { id: "shog", name: "Super Hog Riders", short: "SHog", defaultKeywords: "super hog", category: "Troops" },
  { id: "syeti", name: "Super Yetis", short: "SYeti", defaultKeywords: "super yeti", category: "Troops" },
  // Spells
  { id: "light", name: "Lightning Spell", short: "Light", defaultKeywords: "lightning\nzap", category: "Spells" },
  { id: "heal_sp", name: "Healing Spell", short: "Heal", defaultKeywords: "heal", category: "Spells" },
  { id: "rage", name: "Rage Spell", short: "Rage", defaultKeywords: "rage", category: "Spells" },
  { id: "jump", name: "Jump Spell", short: "Jump", defaultKeywords: "jump", category: "Spells" },
  { id: "freeze", name: "Freeze Spell", short: "Freeze", defaultKeywords: "freeze", category: "Spells" },
  { id: "clone", name: "Clone Spell", short: "Clone", defaultKeywords: "clone", category: "Spells" },
  { id: "invis", name: "Invisibility Spell", short: "Invis", defaultKeywords: "invisibility\ninvis", category: "Spells" },
  { id: "poison", name: "Poison Spell", short: "Poison", defaultKeywords: "poison", category: "Spells" },
  { id: "eq", name: "Earthquake Spell", short: "EQ", defaultKeywords: "earthquake\neq", category: "Spells" },
  { id: "haste", name: "Haste Spell", short: "Haste", defaultKeywords: "haste", category: "Spells" },
  { id: "skel", name: "Skeleton Spell", short: "Skel", defaultKeywords: "skeleton", category: "Spells" },
  { id: "bat", name: "Bat Spell", short: "Bat", defaultKeywords: "bat", category: "Spells" },
  { id: "ogrow", name: "Overgrowth Spell", short: "OGrow", defaultKeywords: "overgrowth", category: "Spells" },
  // Siege Machines
  { id: "ww", name: "Wall Wrecker", short: "WW", defaultKeywords: "wall wrecker\nww", category: "Siege" },
  { id: "bb", name: "Battle Blimp", short: "Blimp", defaultKeywords: "battle blimp\nblimp", category: "Siege" },
  { id: "ss", name: "Stone Slammer", short: "Slam", defaultKeywords: "stone slammer\nslammer", category: "Siege" },
  { id: "sb", name: "Siege Barracks", short: "Barrack", defaultKeywords: "siege barracks\nsb", category: "Siege" },
  { id: "ll", name: "Log Launcher", short: "Log", defaultKeywords: "log launcher\nlog", category: "Siege" },
  { id: "ff", name: "Flame Flinger", short: "Flame", defaultKeywords: "flame flinger\nff", category: "Siege" },
  { id: "bd", name: "Battle Drill", short: "Drill", defaultKeywords: "battle drill\ndrill", category: "Siege" },
  { id: "ts", name: "Troop Launcher", short: "Launch", defaultKeywords: "troop launcher", category: "Siege" },
];

export function DonateTroopsTab() {
  const [unitCategory, setUnitCategory] = useState<"Troops" | "Spells" | "Siege">("Troops");
  const [selectedUnitId, setSelectedUnitId] = useState<string>("barb");

  const [unitConfigs, setUnitConfigs] = useState<
    Record<string, { enabled: boolean; toAll: boolean; keywords: string }>
  >(() => {
    const initial: Record<string, { enabled: boolean; toAll: boolean; keywords: string }> = {};
    DONATE_UNITS.forEach((u) => {
      initial[u.id] = { enabled: false, toAll: false, keywords: u.defaultKeywords };
    });
    return initial;
  });

  const [alphabets, setAlphabets] = useState({
    cyrillic: false,
    chinese: false,
    korean: false,
    persian: false,
  });

  const filteredUnits = DONATE_UNITS.filter((u) => u.category === unitCategory);
  const activeUnit = DONATE_UNITS.find((u) => u.id === selectedUnitId) || filteredUnits[0];
  const currentConfig = unitConfigs[activeUnit.id] || {
    enabled: false,
    toAll: false,
    keywords: activeUnit.defaultKeywords,
  };

  const updateCurrentUnit = (patch: Partial<{ enabled: boolean; toAll: boolean; keywords: string }>) => {
    setUnitConfigs((prev) => ({
      ...prev,
      [activeUnit.id]: { ...currentConfig, ...patch },
    }));
  };

  const handleSelectAllInCategory = () => {
    setUnitConfigs((prev) => {
      const next = { ...prev };
      filteredUnits.forEach((u) => {
        next[u.id] = { ...next[u.id], enabled: true };
      });
      return next;
    });
  };

  const handleResetCategory = () => {
    setUnitConfigs((prev) => {
      const next = { ...prev };
      filteredUnits.forEach((u) => {
        next[u.id] = { ...next[u.id], enabled: false, toAll: false };
      });
      return next;
    });
  };

  return (
    <div className="h-full flex flex-col gap-1.5 overflow-hidden text-[10px]">
      {/* LÆ¯á»šI CHá»ŒN QUÃ‚N (GRID) */}
      <div className="flex-1 bg-slate-900/70 border border-slate-800 rounded-md p-1.5 overflow-hidden flex flex-col">
        <ScrollArea className="flex-1 pr-1">
          <div className="grid grid-cols-9 gap-1">
            {filteredUnits.map((unit) => {
              const isSelected = unit.id === activeUnit.id;
              const isDonateActive = unitConfigs[unit.id]?.enabled;
              return (
                <button
                  key={unit.id}
                  type="button"
                  onClick={() => setSelectedUnitId(unit.id)}
                  title={unit.name}
                  className={`h-8 rounded border flex flex-col items-center justify-center relative transition-all ${
                    isSelected
                      ? "bg-amber-500/20 border-amber-400 text-amber-300 ring-1 ring-amber-400/50"
                      : isDonateActive
                      ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-300"
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-600 hover:text-slate-200"
                  }`}
                >
                  {unitCategory === "Troops" ? (
                    <Swords className="w-3 h-3 mb-0.5 opacity-80" />
                  ) : unitCategory === "Spells" ? (
                    <Sparkles className="w-3 h-3 mb-0.5 opacity-80" />
                  ) : (
                    <Castle className="w-3 h-3 mb-0.5 opacity-80" />
                  )}
                  <span className="text-[8px] font-mono leading-none truncate w-full text-center px-0.5">
                    {unit.short}
                  </span>
                  {isDonateActive && (
                    <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </button>
              );
            })}
          </div>
        </ScrollArea>

        {/* HÃ ng nÃºt All | Reset | Dropdown Category */}
        <div className="flex items-center justify-end gap-1.5 pt-1.5 mt-1 border-t border-slate-800/80">
          <Button
            variant="outline"
            onClick={handleSelectAllInCategory}
            className="h-5 px-2.5 text-[10px] bg-slate-950 border-slate-700 hover:bg-slate-800"
          >
            All
          </Button>
          <Button
            variant="outline"
            onClick={handleResetCategory}
            className="h-5 px-2.5 text-[10px] bg-slate-950 border-slate-700 hover:bg-slate-800"
          >
            Reset
          </Button>
          <Select
            value={unitCategory}
            onValueChange={(val) => {
              const cat = val as "Troops" | "Spells" | "Siege";
              setUnitCategory(cat);
              const first = DONATE_UNITS.find((u) => u.category === cat);
              if (first) setSelectedUnitId(first.id);
            }}
          >
            <SelectTrigger className="h-5 text-[10px] w-[85px] bg-slate-950 border-slate-700 px-2">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
              <SelectItem value="Troops">Troops</SelectItem>
              <SelectItem value="Spells">Spells</SelectItem>
              <SelectItem value="Siege">Siege</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* KHUNG Cáº¤U HÃŒNH KEYWORDS CHO QUÃ‚N ÄANG CHá»ŒN */}
      <div className="grid grid-cols-12 gap-2">
        <fieldset className="col-span-6 border border-slate-800 bg-slate-900/60 rounded-md px-2 py-1">
          <legend className="px-1 text-[10px] font-semibold text-amber-400">
            {activeUnit.name}
          </legend>
          <div className="text-[9px] text-slate-400 mb-1">
            Keywords for donating {activeUnit.name}:
          </div>
          <textarea
            value={currentConfig.keywords}
            onChange={(e) => updateCurrentUnit({ keywords: e.target.value })}
            rows={3}
            className="w-full bg-slate-950 border border-slate-700 rounded p-1 text-[10px] font-mono text-center text-slate-200 resize-none focus:outline-none focus:border-amber-500"
          />
        </fieldset>

        <div className="col-span-6 border border-slate-800 bg-slate-900/60 rounded-md p-2 flex items-center gap-2.5">
          <div className="w-11 h-11 rounded bg-slate-950 border border-slate-700 flex flex-col items-center justify-center shrink-0">
            <Swords className="w-5 h-5 text-amber-400" />
            <span className="text-[8px] font-mono text-slate-400 mt-0.5">{activeUnit.short}</span>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <Checkbox
                id="unit-donate-chk"
                checked={currentConfig.enabled}
                onCheckedChange={(v) => updateCurrentUnit({ enabled: v as boolean })}
                className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
              />
              <label htmlFor="unit-donate-chk" className="text-slate-200 cursor-pointer">
                Donate {activeUnit.name}
              </label>
            </div>

            <div className="flex items-center gap-1.5">
              <Checkbox
                id="unit-donate-all-chk"
                checked={currentConfig.toAll}
                onCheckedChange={(v) => updateCurrentUnit({ toAll: v as boolean })}
                className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-amber-500"
              />
              <label htmlFor="unit-donate-all-chk" className="text-slate-200 cursor-pointer">
                Donate To All
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* EXTRA ALPHABET RECOGNITIONS */}
      <div className="flex items-center justify-between px-1 pt-0.5 text-[10px]">
        <span className="text-slate-400">Extra Alphabet Recognitions:</span>
        {(["cyrillic", "chinese", "korean", "persian"] as const).map((lang) => (
          <div key={lang} className="flex items-center gap-1">
            <Checkbox
              id={`alpha-${lang}`}
              checked={alphabets[lang]}
              onCheckedChange={(v) =>
                setAlphabets((prev) => ({ ...prev, [lang]: v as boolean }))
              }
              className="h-3 w-3 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label htmlFor={`alpha-${lang}`} className="text-slate-300 capitalize cursor-pointer">
              {lang}
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}