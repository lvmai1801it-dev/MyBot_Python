import { useState } from "react";
import {
  Coins,
  Droplet,
  Hammer,
  Trophy,
  Swords,
  ShieldAlert,
  Sparkles,
  Bot,
  Crosshair,
} from "lucide-react";

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

const BB_TROOPS = [
  "None",
  "Raged Barbarian",
  "Sneaky Archer",
  "Boxer Giant",
  "Beta Minion",
  "Bomber",
  "Baby Dragon",
  "Cannon Cart",
  "Night Witch",
  "Drop Ship",
  "Super P.E.K.K.A",
  "Hog Glider",
  "Electrofire Wizard",
  "Battle Machine / Copter",
];

export function BuilderBaseSubTab() {
  // Builders Base Attacking
  const [bbAttack, setBbAttack] = useState(true);
  const [attackCount, setAttackCount] = useState("Random");
  const [nextDelay, setNextDelay] = useState("5");
  const [sameDelay, setSameDelay] = useState("5");

  const [trophiesFilter, setTrophiesFilter] = useState(false);
  const [minTrophy, setMinTrophy] = useState("0");
  const [maxTrophy, setMaxTrophy] = useState("5000");
  const [dropTrophies, setDropTrophies] = useState(false);
  const [starsAvailable, setStarsAvailable] = useState(false);
  const [haltFull, setHaltFull] = useState(true);
  const [ignoreFull, setIgnoreFull] = useState(false);

  // Popup BB Custom Drop Order
  const [showDropOrderModal, setShowDropOrderModal] = useState(false);
  const [enableCustomOrder, setEnableCustomOrder] = useState(false);
  const [dropSlots, setDropSlots] = useState<string[]>(Array(13).fill("None"));

  // Attack Options
  const [attackSide, setAttackSide] = useState<"1" | "2" | "all">("2");
  const [prioritizeDef, setPrioritizeDef] = useState("None");
  const [useTroopSkills, setUseTroopSkills] = useState(false);

  // Collect & Activate
  const [collectRes, setCollectRes] = useState(true);
  const [removeObs, setRemoveObs] = useState(true);
  const [clockTower, setClockTower] = useState(true);
  const [onlyBuilderBusy, setOnlyBuilderBusy] = useState(false);

  // BOB Upgrade
  const [bobUpgrades, setBobUpgrades] = useState({
    battleMachine: false,
    archerTower: false,
    doubleCannon: false,
    battleCopter: false,
    cannon: false,
    multiMortar: false,
  });

  const handleSlotChange = (index: number, val: string) => {
    const updated = [...dropSlots];
    updated[index] = val;
    setDropSlots(updated);
  };

  const handleEmptyDropList = () => {
    setDropSlots(Array(13).fill("None"));
  };

  return (
    <div className="relative h-full overflow-hidden">
      <ScrollArea className="h-full pr-1.5">
        <div className="flex flex-col gap-1.5 pb-1 text-[10px]">
          
          {/* 1. BUILDERS BASE STATS */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              Builders Base Stats
            </legend>
            <div className="grid grid-cols-4 gap-2 items-center py-0.5">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                  <Coins className="w-3.5 h-3.5 text-amber-400" />
                </div>
                <span className="font-mono text-slate-300">---</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-purple-500/15 border border-purple-500/30 flex items-center justify-center">
                  <Droplet className="w-3.5 h-3.5 text-purple-400 fill-purple-400" />
                </div>
                <span className="font-mono text-slate-300">---</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
                  <Hammer className="w-3.5 h-3.5 text-sky-400" />
                </div>
                <span className="font-mono text-slate-300">---</span>
              </div>
              <div className="flex items-center gap-2 justify-end">
                <div className="w-6 h-6 rounded bg-slate-800 border border-slate-700 flex items-center justify-center">
                  <Trophy className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <span className="font-mono text-slate-300">---</span>
              </div>
            </div>
          </fieldset>

          {/* 2. BUILDERS BASE ATTACKING */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              Builders Base Attacking
            </legend>

            <div className="grid grid-cols-12 gap-2">
              {/* Cá»™t trÃ¡i: Attack, Drop Order & Delays (6 cá»™t) */}
              <div className="col-span-6 flex flex-col justify-between gap-1.5 border-r border-slate-800/80 pr-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Swords className="w-3.5 h-3.5 text-emerald-400" />
                    <Checkbox
                      id="bb-attack"
                      checked={bbAttack}
                      onCheckedChange={(v) => setBbAttack(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                    />
                    <label htmlFor="bb-attack" className="text-slate-200 font-medium cursor-pointer">
                      Attack
                    </label>
                  </div>

                  <div className="flex items-center gap-1">
                    <span className="text-slate-400 text-[9px]">Count</span>
                    <Select value={attackCount} onValueChange={setAttackCount}>
                      <SelectTrigger className="h-5 text-[10px] w-[68px] bg-slate-950 border-slate-700 px-1.5">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                        <SelectItem value="Random">Random</SelectItem>
                        {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
                          <SelectItem key={n} value={String(n)}>
                            {n}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <Button
                    onClick={() => setShowDropOrderModal(true)}
                    className={`h-6 px-2 text-[10px] font-bold border ${
                      enableCustomOrder
                        ? "bg-emerald-600 hover:bg-emerald-700 border-emerald-400 text-white"
                        : "bg-rose-600 hover:bg-rose-700 border-rose-400 text-white"
                    }`}
                  >
                    Drop Order
                  </Button>

                  <div className="flex items-center gap-1">
                    <span className="text-slate-300 text-[9px]">Next Troop Delay</span>
                    <Select value={nextDelay} onValueChange={setNextDelay}>
                      <SelectTrigger className="h-5 text-[10px] w-11 bg-slate-950 border-slate-700 px-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                          <SelectItem key={n} value={String(n)}>
                            {n}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-1">
                  <span className="text-slate-300 text-[9px]">Same Troop Delay</span>
                  <Select value={sameDelay} onValueChange={setSameDelay}>
                    <SelectTrigger className="h-5 text-[10px] w-11 bg-slate-950 border-slate-700 px-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                        <SelectItem key={n} value={String(n)}>
                          {n}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Cá»™t pháº£i: Trophies & Storages Checkboxes (6 cá»™t) */}
              <div className="col-span-6 flex flex-col justify-between gap-1">
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="bb-trophies"
                      checked={trophiesFilter}
                      onCheckedChange={(v) => setTrophiesFilter(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="bb-trophies" className="text-slate-200 cursor-pointer">
                      Trophies
                    </label>
                  </div>
                  <div className="flex items-center gap-1">
                    <Input
                      disabled={!trophiesFilter}
                      value={minTrophy}
                      onChange={(e) => setMinTrophy(e.target.value)}
                      className="h-5 w-11 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                    />
                    <Input
                      disabled={!trophiesFilter}
                      value={maxTrophy}
                      onChange={(e) => setMaxTrophy(e.target.value)}
                      className="h-5 w-12 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="bb-drop-trophy"
                      checked={dropTrophies}
                      onCheckedChange={(v) => setDropTrophies(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="bb-drop-trophy" className="text-slate-200 cursor-pointer">
                      Drop Trophies
                    </label>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="bb-stars"
                      checked={starsAvailable}
                      onCheckedChange={(v) => setStarsAvailable(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="bb-stars" className="text-slate-200 cursor-pointer">
                      Stars Available
                    </label>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <Checkbox
                    id="bb-halt-full"
                    checked={haltFull}
                    onCheckedChange={(v) => setHaltFull(v as boolean)}
                    className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                  />
                  <label htmlFor="bb-halt-full" className="text-slate-200 cursor-pointer">
                    Halt When Storages Are Full
                  </label>
                </div>

                <div className="flex items-center gap-1.5">
                  <Checkbox
                    id="bb-ignore-full"
                    checked={ignoreFull}
                    onCheckedChange={(v) => setIgnoreFull(v as boolean)}
                    className="h-3.5 w-3.5 border-slate-600"
                  />
                  <label htmlFor="bb-ignore-full" className="text-slate-200 cursor-pointer">
                    Ignore Full Storages
                  </label>
                </div>
              </div>
            </div>
          </fieldset>

          {/* 3. ATTACK OPTIONS */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              Attack Options
            </legend>

            <div className="flex items-center justify-between mb-1.5">
              <span className="text-slate-300">Attack Sides:</span>
              <div className="flex items-center gap-5 pr-4">
                {[
                  { id: "1", label: "1 Side" },
                  { id: "2", label: "2 Sides" },
                  { id: "all", label: "All Sides" },
                ].map((side) => (
                  <div key={side.id} className="flex items-center gap-1.5">
                    <Checkbox
                      id={`side-${side.id}`}
                      checked={attackSide === side.id}
                      onCheckedChange={() => setAttackSide(side.id as "1" | "2" | "all")}
                      className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                    />
                    <label htmlFor={`side-${side.id}`} className="text-slate-200 cursor-pointer">
                      {side.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-1">
                <span className="text-slate-300 whitespace-nowrap">Prioritize Defenses:</span>
                <Select value={prioritizeDef} onValueChange={setPrioritizeDef}>
                  <SelectTrigger className="h-6 text-[10px] flex-1 bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                    <SelectItem value="None">None</SelectItem>
                    <SelectItem value="Lava Launcher">Lava Launcher</SelectItem>
                    <SelectItem value="Air Bomb">Air Bomb</SelectItem>
                    <SelectItem value="Mega Tesla">Mega Tesla</SelectItem>
                    <SelectItem value="Guard Post">Guard Post</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="bb-troop-skills"
                  checked={useTroopSkills}
                  onCheckedChange={(v) => setUseTroopSkills(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <label htmlFor="bb-troop-skills" className="text-slate-200 cursor-pointer">
                  Use Troop Skills
                </label>
              </div>
            </div>
          </fieldset>

          {/* 4. COLLECT & ACTIVATE */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              Collect & Activate
            </legend>
            <div className="grid grid-cols-2 gap-y-1.5 gap-x-2">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="bb-col-res"
                  checked={collectRes}
                  onCheckedChange={(v) => setCollectRes(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="bb-col-res" className="text-slate-200 cursor-pointer">
                  Collect Resources
                </label>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="bb-rem-obs"
                  checked={removeObs}
                  onCheckedChange={(v) => setRemoveObs(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="bb-rem-obs" className="text-slate-200 cursor-pointer">
                  Remove Obstacles
                </label>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="bb-clock"
                  checked={clockTower}
                  onCheckedChange={(v) => setClockTower(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="bb-clock" className="text-slate-200 cursor-pointer">
                  Activate Clock Tower Boost
                </label>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="bb-busy-only"
                  checked={onlyBuilderBusy}
                  onCheckedChange={(v) => setOnlyBuilderBusy(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <label htmlFor="bb-busy-only" className="text-slate-200 cursor-pointer">
                  Only When Builder Is Busy
                </label>
              </div>
            </div>
          </fieldset>

          {/* 5. BOB UPGRADE (6 CHECKBOXES) */}
          <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              BOB Upgrade
            </legend>
            <div className="grid grid-cols-3 gap-y-1.5 gap-x-2">
              {[
                { key: "battleMachine", label: "Battle Machine", icon: Bot, color: "text-amber-400" },
                { key: "archerTower", label: "Archer Tower", icon: Crosshair, color: "text-emerald-400" },
                { key: "doubleCannon", label: "Double Cannon", icon: ShieldAlert, color: "text-sky-400" },
                { key: "battleCopter", label: "Battle Copter", icon: Sparkles, color: "text-orange-400" },
                { key: "cannon", label: "Cannon", icon: ShieldAlert, color: "text-slate-300" },
                { key: "multiMortar", label: "Multi Mortar", icon: ShieldAlert, color: "text-rose-400" },
              ].map((item) => {
                const IconComp = item.icon;
                const isChecked = bobUpgrades[item.key as keyof typeof bobUpgrades];
                return (
                  <div key={item.key} className="flex items-center gap-1.5">
                    <IconComp className={`w-3.5 h-3.5 shrink-0 ${item.color}`} />
                    <Checkbox
                      id={`bob-${item.key}`}
                      checked={isChecked}
                      onCheckedChange={(v) =>
                        setBobUpgrades((prev) => ({ ...prev, [item.key]: v as boolean }))
                      }
                      className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                    />
                    <label htmlFor={`bob-${item.key}`} className="text-slate-200 cursor-pointer truncate">
                      {item.label}
                    </label>
                  </div>
                );
              })}
            </div>
          </fieldset>

        </div>
      </ScrollArea>

      {/* POPUP MODAL: BB CUSTOM DROP ORDER (Giá»‘ng áº£nh 2 cá»§a báº¡n) */}
      {showDropOrderModal && (
        <div className="absolute inset-0 z-50 bg-slate-950/80 backdrop-blur-[1px] flex items-center justify-center p-2">
          <div className="w-full max-w-[390px] bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-3 text-[11px]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-2">
              <span className="font-bold text-slate-100">BB Custom Drop Order</span>
              <span className="text-[10px] text-slate-400">13 Slots</span>
            </div>

            <fieldset className="border border-slate-800 bg-slate-950/60 rounded-md p-2.5">
              <legend className="px-1 text-[10px] text-slate-400">
                BB Custom Dropping Order
              </legend>

              <div className="flex items-center gap-2 mb-2.5">
                <Checkbox
                  id="enable-bb-drop"
                  checked={enableCustomOrder}
                  onCheckedChange={(v) => setEnableCustomOrder(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="enable-bb-drop" className="text-slate-200 font-medium cursor-pointer">
                  Enable Custom Dropping Order
                </label>
              </div>

              {/* 13 Ã” Dropdown chia 2 cá»™t: Cá»™t 1 (1-6), Cá»™t 2 (7-13) */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mb-3">
                {/* Cá»™t trÃ¡i: 1 -> 6 */}
                <div className="flex flex-col gap-1.5">
                  {[0, 1, 2, 3, 4, 5].map((idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <span className="w-4 text-right font-mono text-slate-400">{idx + 1}:</span>
                      <Select
                        disabled={!enableCustomOrder}
                        value={dropSlots[idx]}
                        onValueChange={(val) => handleSlotChange(idx, val)}
                      >
                        <SelectTrigger className="h-5 text-[10px] flex-1 bg-slate-900 border-slate-700 px-1.5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                          {BB_TROOPS.map((t) => (
                            <SelectItem key={t} value={t}>
                              {t}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>

                {/* Cá»™t pháº£i: 7 -> 13 */}
                <div className="flex flex-col gap-1.5">
                  {[6, 7, 8, 9, 10, 11, 12].map((idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <span className="w-4 text-right font-mono text-slate-400">{idx + 1}:</span>
                      <Select
                        disabled={!enableCustomOrder}
                        value={dropSlots[idx]}
                        onValueChange={(val) => handleSlotChange(idx, val)}
                      >
                        <SelectTrigger className="h-5 text-[10px] flex-1 bg-slate-900 border-slate-700 px-1.5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                          {BB_TROOPS.map((t) => (
                            <SelectItem key={t} value={t}>
                              {t}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
              </div>

              {/* 2 NÃºt Apply & Empty */}
              <div className="grid grid-cols-2 gap-2">
                <Button
                  disabled={!enableCustomOrder}
                  onClick={() => setShowDropOrderModal(false)}
                  className="h-6 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  Apply New Order
                </Button>
                <Button
                  disabled={!enableCustomOrder}
                  variant="outline"
                  onClick={handleEmptyDropList}
                  className="h-6 text-[10px] border-slate-700 bg-slate-900 hover:bg-slate-800"
                >
                  Empty Drop List
                </Button>
              </div>
            </fieldset>

            <div className="flex justify-end mt-2.5">
              <Button
                variant="secondary"
                onClick={() => setShowDropOrderModal(false)}
                className="h-6 px-4 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}