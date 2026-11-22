import React, { useState } from "react";
import { Trash2, Swords, Sparkles, Castle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ArmyUnit {
  id: string;
  name: string;
  short: string;
  housing: number;
  category: "Elixir" | "Dark" | "Event" | "Super" | "Spells" | "Sieges";
}

const ARMY_UNITS: ArmyUnit[] = [
  // Elixir Troops
  { id: "barb", name: "Barbarian", short: "Barb", housing: 1, category: "Elixir" },
  { id: "arch", name: "Archer", short: "Arch", housing: 1, category: "Elixir" },
  { id: "giant", name: "Giant", short: "Giant", housing: 5, category: "Elixir" },
  { id: "gob", name: "Goblin", short: "Gob", housing: 1, category: "Elixir" },
  { id: "wb", name: "Wall Breaker", short: "WB", housing: 2, category: "Elixir" },
  { id: "loon", name: "Balloon", short: "Loon", housing: 5, category: "Elixir" },
  { id: "wiz", name: "Wizard", short: "Wiz", housing: 4, category: "Elixir" },
  { id: "heal", name: "Healer", short: "Heal", housing: 14, category: "Elixir" },
  { id: "drag", name: "Dragon", short: "Drag", housing: 20, category: "Elixir" },
  { id: "pekka", name: "P.E.K.K.A", short: "Pekka", housing: 25, category: "Elixir" },
  { id: "bdrag", name: "Baby Dragon", short: "BDrag", housing: 10, category: "Elixir" },
  { id: "miner", name: "Miner", short: "Miner", housing: 6, category: "Elixir" },
  { id: "edrag", name: "Electro Dragon", short: "EDrag", housing: 30, category: "Elixir" },
  { id: "yeti", name: "Yeti", short: "Yeti", housing: 18, category: "Elixir" },
  { id: "drider", name: "Dragon Rider", short: "DRider", housing: 25, category: "Elixir" },
  { id: "etitan", name: "Electro Titan", short: "ETitan", housing: 32, category: "Elixir" },
  { id: "rrider", name: "Root Rider", short: "RRider", housing: 20, category: "Elixir" },
  { id: "thrower", name: "Thrower", short: "Throw", housing: 16, category: "Elixir" },
  // Dark Elixir Troops
  { id: "minion", name: "Minion", short: "Minion", housing: 2, category: "Dark" },
  { id: "hog", name: "Hog Rider", short: "Hog", housing: 5, category: "Dark" },
  { id: "valk", name: "Valkyrie", short: "Valk", housing: 8, category: "Dark" },
  { id: "golem", name: "Golem", short: "Golem", housing: 30, category: "Dark" },
  { id: "witch", name: "Witch", short: "Witch", housing: 12, category: "Dark" },
  { id: "hound", name: "Lava Hound", short: "Hound", housing: 30, category: "Dark" },
  { id: "bowler", name: "Bowler", short: "Bowler", housing: 6, category: "Dark" },
  { id: "igolem", name: "Ice Golem", short: "IGolem", housing: 15, category: "Dark" },
  { id: "hh", name: "Headhunter", short: "HH", housing: 6, category: "Dark" },
  { id: "druid", name: "Druid", short: "Druid", housing: 16, category: "Dark" },
  // Super Troops
  { id: "sbarb", name: "Super Barbarian", short: "SBarb", housing: 5, category: "Super" },
  { id: "sarch", name: "Super Archer", short: "SArch", housing: 12, category: "Super" },
  { id: "sgob", name: "Sneaky Goblin", short: "Sneaky", housing: 3, category: "Super" },
  { id: "swb", name: "Super Wall Breaker", short: "SWB", housing: 8, category: "Super" },
  { id: "rloon", name: "Rocket Balloon", short: "RLoon", housing: 8, category: "Super" },
  { id: "swiz", name: "Super Wizard", short: "SWiz", housing: 10, category: "Super" },
  { id: "sdrag", name: "Super Dragon", short: "SDrag", housing: 40, category: "Super" },
  // Spells
  { id: "light", name: "Lightning", short: "Light", housing: 1, category: "Spells" },
  { id: "heal_sp", name: "Heal", short: "Heal", housing: 2, category: "Spells" },
  { id: "rage", name: "Rage", short: "Rage", housing: 2, category: "Spells" },
  { id: "jump", name: "Jump", short: "Jump", housing: 2, category: "Spells" },
  { id: "freeze", name: "Freeze", short: "Freeze", housing: 1, category: "Spells" },
  { id: "poison", name: "Poison", short: "Poison", housing: 1, category: "Spells" },
  { id: "eq", name: "Earthquake", short: "EQ", housing: 1, category: "Spells" },
  { id: "haste", name: "Haste", short: "Haste", housing: 1, category: "Spells" },
  // Sieges
  { id: "ww", name: "Wall Wrecker", short: "WW", housing: 1, category: "Sieges" },
  { id: "bb", name: "Battle Blimp", short: "Blimp", housing: 1, category: "Sieges" },
  { id: "ss", name: "Stone Slammer", short: "Slam", housing: 1, category: "Sieges" },
  { id: "sb", name: "Siege Barracks", short: "Barrack", housing: 1, category: "Sieges" },
  { id: "ll", name: "Log Launcher", short: "Log", housing: 1, category: "Sieges" },
  { id: "ff", name: "Flame Flinger", short: "Flame", housing: 1, category: "Sieges" },
];

export function TrainArmyTab() {
  const [forceCamp, setForceCamp] = useState(true);
  const [campSize, setCampSize] = useState("220");
  const [fullCampPercent, setFullCampPercent] = useState("100");
  const [spellCapacity, setSpellCapacity] = useState("0");
  const [activeCat, setActiveCat] = useState<ArmyUnit["category"]>("Elixir");

  // Khởi tạo đội hình Barch + Goblin + WB khớp với ảnh chụp của bạn[cite: 23]
  const [counts, setCounts] = useState<Record<string, number>>({
    barb: 58,
    arch: 115,
    giant: 4,
    gob: 19,
    wb: 4,
  });

  const updateCount = (id: string, val: number) => {
    setCounts((prev) => ({ ...prev, [id]: Math.max(0, val) }));
  };

  // Tính tổng sức chứa đang chọn
  const selectedTroops = ARMY_UNITS.filter(
    (u) => !["Spells", "Sieges"].includes(u.category) && (counts[u.id] || 0) > 0
  );
  const selectedSpells = ARMY_UNITS.filter(
    (u) => u.category === "Spells" && (counts[u.id] || 0) > 0
  );
  const selectedSieges = ARMY_UNITS.filter(
    (u) => u.category === "Sieges" && (counts[u.id] || 0) > 0
  );

  const totalTroopHousing = selectedTroops.reduce(
    (sum, u) => sum + u.housing * (counts[u.id] || 0),
    0
  );
  const totalSpellHousing = selectedSpells.reduce(
    (sum, u) => sum + u.housing * (counts[u.id] || 0),
    0
  );

  const maxCamp = Number(campSize) || 220;
  const maxSpell = Number(spellCapacity) || 11;

  return (
    <div className="h-full flex flex-col gap-1.5 overflow-hidden text-[10px]">
      {/* HÀNG TRÊN: FORCE ARMY CAMP & SPELL CAPACITY[cite: 23] */}
      <div className="flex items-center justify-between bg-slate-900/80 border border-slate-800 rounded px-2 py-1">
        <Button
          variant="destructive"
          size="icon"
          onClick={() => setCounts({})}
          title="Clear Army"
          className="h-5 w-5 bg-rose-600 hover:bg-rose-700"
        >
          <Trash2 className="w-3 h-3" />
        </Button>

        <div className="flex items-center gap-1">
          <Checkbox
            id="force-camp"
            checked={forceCamp}
            onCheckedChange={(v) => setForceCamp(v as boolean)}
            className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
          />
          <label htmlFor="force-camp" className="text-slate-200 cursor-pointer">
            Force Army Camp:
          </label>
          <Input
            value={campSize}
            onChange={(e) => setCampSize(e.target.value)}
            className="h-5 w-11 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
          />
        </div>

        <div className="flex items-center gap-1">
          <span className="text-slate-300">'Full' Camp ≥</span>
          <Input
            value={fullCampPercent}
            onChange={(e) => setFullCampPercent(e.target.value)}
            className="h-5 w-10 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
          />
          <span className="text-slate-400">%</span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-slate-300">Spell Cap:</span>
          <Select value={spellCapacity} onValueChange={setSpellCapacity}>
            <SelectTrigger className="h-5 text-[10px] w-11 bg-slate-950 border-slate-700 px-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
              {["0", "2", "4", "6", "7", "9", "11"].map((v) => (
                <SelectItem key={v} value={v}>
                  {v}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* KHU VỰC HIỂN THỊ QUÂN ĐÃ CHỌN + MENU DANH MỤC BÊN PHẢI[cite: 23] */}
      <div className="grid grid-cols-12 gap-1.5">
        {/* Cột trái (8 cột): Troops & Spells đã chọn */}
        <div className="col-span-8 flex flex-col gap-1.5">
          {/* Box Troops[cite: 23] */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded px-2 py-1">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">Troops</legend>
            <div className="h-10 flex items-center gap-1.5 overflow-x-auto">
              {selectedTroops.length === 0 ? (
                <span className="text-slate-600 italic text-[10px]">No troops selected</span>
              ) : (
                selectedTroops.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => updateCount(u.id, (counts[u.id] || 0) - 1)}
                    title="Click to remove 1"
                    className="h-9 min-w-[34px] px-1 bg-slate-950 border border-slate-700 hover:border-rose-500 rounded flex flex-col items-center justify-center shrink-0"
                  >
                    <span className="text-[8px] text-slate-300 truncate max-w-[32px]">{u.short}</span>
                    <span className="text-[10px] font-bold font-mono text-sky-400 leading-none mt-0.5">
                      {counts[u.id]}
                    </span>
                  </button>
                ))
              )}
            </div>
            {/* Progress bar sức chứa */}
            <div className="flex items-center gap-1.5 mt-1">
              <div className="flex-1 h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  className={`h-full transition-all ${
                    totalTroopHousing > maxCamp ? "bg-rose-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(100, (totalTroopHousing / maxCamp) * 100)}%` }}
                />
              </div>
              <span className="px-1.5 py-0.2 bg-emerald-600 text-white font-mono font-bold text-[9px] rounded">
                {totalTroopHousing}
              </span>
            </div>
          </fieldset>

          {/* Box Spells[cite: 23] */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded px-2 py-1">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">Spells</legend>
            <div className="h-8 flex items-center gap-1.5 overflow-x-auto">
              {selectedSpells.length === 0 ? (
                <span className="text-slate-600 italic text-[10px]">No spells selected</span>
              ) : (
                selectedSpells.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => updateCount(u.id, (counts[u.id] || 0) - 1)}
                    className="h-7 min-w-[32px] px-1 bg-slate-950 border border-slate-700 hover:border-rose-500 rounded flex flex-col items-center justify-center shrink-0"
                  >
                    <span className="text-[8px] text-slate-300">{u.short}</span>
                    <span className="text-[9px] font-bold font-mono text-purple-400 leading-none">
                      {counts[u.id]}
                    </span>
                  </button>
                ))
              )}
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              <div className="flex-1 h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full bg-purple-500 transition-all"
                  style={{ width: `${Math.min(100, (totalSpellHousing / maxSpell) * 100)}%` }}
                />
              </div>
              <span className="px-1.5 py-0.2 bg-emerald-600 text-white font-mono font-bold text-[9px] rounded">
                {totalSpellHousing}
              </span>
            </div>
          </fieldset>
        </div>

        {/* Cột phải (4 cột): Sieges & Các nút chọn nhóm quân[cite: 23] */}
        <div className="col-span-4 flex flex-col justify-between gap-1">
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded px-1.5 py-1 h-12">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">Sieges</legend>
            <div className="flex items-center gap-1 overflow-x-auto">
              {selectedSieges.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => updateCount(u.id, (counts[u.id] || 0) - 1)}
                  className="h-7 px-1 bg-slate-950 border border-slate-700 rounded flex flex-col items-center justify-center"
                >
                  <span className="text-[8px] text-amber-300">{u.short}</span>
                  <span className="text-[9px] font-mono text-white">{counts[u.id]}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {/* Các nút chuyển danh mục đen giống ảnh[cite: 23] */}
          <div className="flex flex-col gap-0.5">
            {(["Elixir", "Dark", "Event", "Super"] as const).map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCat(cat)}
                className={`h-5 rounded text-[10px] font-bold border transition-all ${
                  activeCat === cat
                    ? "bg-slate-950 border-amber-400 text-amber-400"
                    : "bg-slate-950 border-slate-800 text-slate-200 hover:border-slate-600"
                }`}
              >
                {cat === "Dark" ? "Dark Elixir Troops" : `${cat} Troops`}
              </button>
            ))}
            <div className="grid grid-cols-2 gap-0.5">
              <button
                type="button"
                onClick={() => setActiveCat("Spells")}
                className={`h-5 rounded text-[10px] font-bold border ${
                  activeCat === "Spells"
                    ? "bg-slate-950 border-amber-400 text-amber-400"
                    : "bg-slate-950 border-slate-800 text-slate-200"
                }`}
              >
                Spells
              </button>
              <button
                type="button"
                onClick={() => setActiveCat("Sieges")}
                className={`h-5 rounded text-[10px] font-bold border ${
                  activeCat === "Sieges"
                    ? "bg-slate-950 border-amber-400 text-amber-400"
                    : "bg-slate-950 border-slate-800 text-slate-200"
                }`}
              >
                Sieges
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* LƯỚI NHẬP SỐ LƯỢNG QUÂN Ở DƯỚI CÙNG[cite: 23] */}
      <div className="flex-1 bg-slate-900/70 border border-slate-800 rounded p-1.5 overflow-hidden flex flex-col">
        <ScrollArea className="flex-1 pr-1">
          <div className="grid grid-cols-9 gap-1">
            {ARMY_UNITS.filter((u) => u.category === activeCat).map((unit) => {
              const qty = counts[unit.id] || 0;
              return (
                <div
                  key={unit.id}
                  className="bg-slate-950 border border-slate-800 rounded p-0.5 flex flex-col items-center"
                >
                  <button
                    type="button"
                    onClick={() => updateCount(unit.id, qty + 1)}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      updateCount(unit.id, qty - 1);
                    }}
                    title={`${unit.name} (Click +1, Right-Click -1)`}
                    className="w-full h-7 rounded bg-slate-900 hover:bg-slate-800 flex flex-col items-center justify-center mb-0.5"
                  >
                    {activeCat === "Spells" ? (
                      <Sparkles className="w-3 h-3 text-purple-400" />
                    ) : activeCat === "Sieges" ? (
                      <Castle className="w-3 h-3 text-amber-400" />
                    ) : (
                      <Swords className="w-3 h-3 text-sky-400" />
                    )}
                    <span className="text-[8px] font-mono text-slate-300 leading-none mt-0.5">
                      {unit.short}
                    </span>
                  </button>
                  <input
                    type="number"
                    min={0}
                    value={qty}
                    onChange={(e) => updateCount(unit.id, parseInt(e.target.value) || 0)}
                    className="w-full h-4 bg-slate-900 border border-slate-700 rounded text-center font-mono text-[10px] text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}