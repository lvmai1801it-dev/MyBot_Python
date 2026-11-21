import { useState } from "react";
import {
  Trophy,
  Clock,
  Award,
  Settings2,
  ChevronRight,
  ChevronDown,
  Hammer,
} from "lucide-react";

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

interface ChallengeCategory {
  id: string;
  label: string;
  items: string[];
}

// ToÃ n bá»™ 11 nhÃ³m nhiá»‡m vá»¥ bÃ³c tÃ¡ch Ä‘áº§y Ä‘á»§ tá»« 8 áº£nh cá»§a báº¡n
const CLAN_GAMES_TREE: ChallengeCategory[] = [
  {
    id: "hero",
    label: "Hero Challenges",
    items: [
      "King Commander",
      "Queen Supreme",
      "Prince Patrol",
      "Grand Stand",
      "Reigning Champion",
      "Duke Unchained",
      "Hero Level Hunter",
      "King Level Hunter",
      "Queen Level Hunter",
      "Warden Level Hunter",
      "Champion Level Hunter",
    ],
  },
  {
    id: "loot",
    label: "Loot Challenges",
    items: [
      "Gold Challenge",
      "Gold Grab",
      "Elixir Challenge",
      "Elixir Embezzlement",
      "Dark Elixir Challenge",
      "Dark Elixir Heist",
    ],
  },
  {
    id: "battle",
    label: "Battle Challenges",
    items: [
      "Star Collector",
      "Hunt for Three Stars",
      "Pile of Victories",
      "Winning Streak",
      "Lord of Destruction",
      "No Heroics Allowed",
      "No-Magic Zone",
      "Super Charge!",
    ],
  },
  {
    id: "destruction",
    label: "Destruction Challenges",
    items: [
      "Air Defenses",
      "Air Sweepers",
      "Archer Tower",
      "Bomb Towers",
      "Builder Hut",
      "Cannon",
      "Eagle Artillery",
      "Inferno Towers",
      "Mortar",
      "Scattershot",
      "Tesla Towers",
      "Wizard Tower",
      "X-Bows",
      "Gold Mine",
      "Elixir Pump",
      "Dark Elixir Drill",
      "Gold Storage",
      "Elixir Storage",
      "Dark Elixir Storage",
      "Army Camp",
      "Clan Castle",
      "Laboratory",
      "Spell Factory",
      "Dark Spell Factory",
      "Building Breakdown",
      "Wall Whacker",
    ],
  },
  {
    id: "air_troop",
    label: "Air Troop Challenges",
    items: [
      "Balloon",
      "Dragon",
      "Baby Dragon",
      "Electro Dragon",
      "Dragon Rider",
      "Minion",
      "Lava Hound",
      "Rocket Balloon",
      "Super Dragon",
      "Inferno Dragon",
      "Super Minion",
      "Ice Hound",
      "Battle Blimp",
      "Stone Slammer",
    ],
  },
  {
    id: "ground_troop",
    label: "Ground Troop Challenges",
    items: [
      "Barbarian",
      "Archer",
      "Giant",
      "Goblin",
      "Wall Breaker",
      "Wizard",
      "Healer",
      "P.E.K.K.A",
      "Miner",
      "Yeti",
      "Hog Rider",
      "Valkyrie",
      "Golem",
      "Witch",
      "Bowler",
      "Ice Golem",
      "Headhunter",
      "Super Barbarian",
      "Super Archer",
      "Super Giant",
      "Sneaky Goblin",
      "Super Wall Breaker",
      "Super Wizard",
      "Super Miner",
      "Super Yeti",
      "Super Hog Rider",
      "Super Valkyrie",
      "Super Witch",
      "Super Bowler",
      "Wall Wrecker",
      "Siege Barracks",
      "Log Launcher",
    ],
  },
  {
    id: "misc",
    label: "Miscellaneous Challenges",
    items: ["Helping Hand", "Donate Spells", "Gardening Exercise"],
  },
  {
    id: "spell",
    label: "Spell Challenges",
    items: [
      "Lightning",
      "Heal",
      "Rage",
      "Jump",
      "Freeze",
      "Clone",
      "Invisibility",
      "Poison",
      "Earthquake",
      "Haste",
      "Skeleton",
      "Bat",
    ],
  },
  {
    id: "bb_battle",
    label: "BB Battle Challenges",
    items: ["Star Master", "Victories", "Destructor", "Sudden Stars"],
  },
  {
    id: "bb_destruction",
    label: "BB Destruction Challenges",
    items: [
      "Air Bomb",
      "Archer Tower",
      "Cannon",
      "Crusher",
      "Double Cannon",
      "Firecrackers",
      "Giant Cannon",
      "Guard Post",
      "Lava Launcher",
      "Mega Tesla",
      "Multi Mortar",
      "Roaster",
      "X-Bow Explosion",
      "Builder Hall",
      "O.T.T.O's Outpost",
      "Star Laboratory",
      "Clock Tower",
      "Healing Hut",
      "Gem Mine",
      "Building Breakdown",
      "Wall Wipeout",
    ],
  },
  {
    id: "bb_troop",
    label: "BB Troop Challenges",
    items: [
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
    ],
  },
];

export function ClanGamesSubTab() {
  // Tráº¡ng thÃ¡i mÃ n hÃ¬nh chÃ­nh Clan Games
  const [enabled, setEnabled] = useState(false);
  const [disableUponComplete, setDisableUponComplete] = useState(false);
  const [collectRewards, setCollectRewards] = useState(false);

  // Popup ClanGames Challenge Settings
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({
    hero: true,
    loot: true,
    battle: true,
  });
  const [selectedChallenges, setSelectedChallenges] = useState<Record<string, boolean>>({});
  const [focusedItem, setFocusedItem] = useState<string | null>(null);

  // TÃ¹y chá»n cá»™t pháº£i cá»§a Modal
  const [alwaysForceAttack, setAlwaysForceAttack] = useState(false);
  const [purgeUnselected, setPurgeUnselected] = useState(false);
  const [reservePointsPurge, setReservePointsPurge] = useState(false);
  const [challengeDurationFilter, setChallengeDurationFilter] = useState<"all" | "no_1day">("all");
  const [sortingEnabled, setSortingEnabled] = useState(true);
  const [sortingMode, setSortingMode] = useState("Lower Difficulties");
  const [prioritySelect, setPrioritySelect] = useState<"bb" | "main" | "equal">("equal");

  const toggleExpand = (catId: string) => {
    setExpandedCats((prev) => ({ ...prev, [catId]: !prev[catId] }));
  };

  // TÃ­ch chá»n cáº£ nhÃ³m hoáº·c tá»«ng má»¥c con
  const toggleCategory = (cat: ChallengeCategory, checked: boolean) => {
    const next = { ...selectedChallenges };
    cat.items.forEach((item) => {
      next[`${cat.id}:${item}`] = checked;
    });
    setSelectedChallenges(next);
  };

  const toggleItem = (catId: string, item: string, checked: boolean) => {
    setSelectedChallenges((prev) => ({
      ...prev,
      [`${catId}:${item}`]: checked,
    }));
  };

  const isCategoryChecked = (cat: ChallengeCategory) =>
    cat.items.length > 0 && cat.items.every((item) => selectedChallenges[`${cat.id}:${item}`]);

  return (
    <div className="relative h-full flex flex-col gap-1.5 overflow-hidden text-[11px]">
      {/* KHUNG TRÃŠN: CLAN GAMES CONTROLS */}
      <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-2">
        <legend className="px-1 text-[10px] font-semibold text-slate-400">
          Clan Games
        </legend>

        <div className="grid grid-cols-12 gap-2.5">
          {/* Cá»˜T TRÃI (4 cá»™t): Icon & Stats */}
          <div className="col-span-4 flex flex-col justify-between gap-1.5">
            <div className="flex flex-col items-center justify-center py-1 bg-slate-950/60 border border-slate-800/80 rounded">
              <div className="w-9 h-9 rounded-full bg-amber-500/15 border border-amber-500/40 flex items-center justify-center mb-1">
                <Hammer className="w-5 h-5 text-amber-400" />
              </div>
              <span className="text-[10px] font-semibold text-amber-300">Strongman</span>
            </div>

            <div className="border border-slate-800 bg-slate-950/80 rounded px-2 py-1 text-center">
              <div className="text-[9px] text-slate-400 flex items-center justify-center gap-1">
                <Clock className="w-2.5 h-2.5 text-sky-400" /> Time Remaining
              </div>
              <div className="font-mono font-bold text-slate-200 text-xs mt-0.5">N/A</div>
            </div>

            <div className="border border-slate-800 bg-slate-950/80 rounded px-2 py-1 text-center">
              <div className="text-[9px] text-slate-400 flex items-center justify-center gap-1">
                <Trophy className="w-2.5 h-2.5 text-amber-400" /> Your Score
              </div>
              <div className="font-mono font-bold text-slate-200 text-xs mt-0.5">N/A</div>
            </div>
          </div>

          {/* Cá»˜T PHáº¢I (8 cá»™t): Checkboxes, Challenges & Rewards */}
          <div className="col-span-8 flex flex-col justify-between gap-2">
            <div className="flex items-center justify-between pt-0.5">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="cg-enabled"
                  checked={enabled}
                  onCheckedChange={(v) => setEnabled(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="cg-enabled" className="text-slate-200 font-medium cursor-pointer">
                  Enabled
                </label>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="cg-disable-complete"
                  disabled={!enabled}
                  checked={disableUponComplete}
                  onCheckedChange={(v) => setDisableUponComplete(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label
                  htmlFor="cg-disable-complete"
                  className={`cursor-pointer ${enabled ? "text-slate-200" : "text-slate-500"}`}
                >
                  Disable Upon Completion
                </label>
              </div>
            </div>

            {/* Khung Challenges */}
            <fieldset className="border border-slate-800 bg-slate-950/50 rounded px-2.5 py-2.5 flex items-center justify-center">
              <legend className="px-1 text-[10px] text-slate-400">Challenges</legend>
              <Button
                disabled={!enabled}
                onClick={() => setShowSettingsModal(true)}
                className="h-7 px-4 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 disabled:opacity-40"
              >
                <Settings2 className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
                Clan Games Settings
              </Button>
            </fieldset>

            {/* Khung Rewards */}
            <fieldset className="border border-slate-800 bg-slate-950/50 rounded px-2.5 py-2">
              <legend className="px-1 text-[10px] text-slate-400">Rewards</legend>
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="cg-collect-rewards"
                  disabled={!enabled}
                  checked={collectRewards}
                  onCheckedChange={(v) => setCollectRewards(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label
                  htmlFor="cg-collect-rewards"
                  className={`flex items-center gap-1 cursor-pointer ${
                    enabled ? "text-slate-200" : "text-slate-500"
                  }`}
                >
                  <Award className="w-3.5 h-3.5 text-amber-400" /> Collect
                </label>
              </div>
            </fieldset>
          </div>
        </div>
      </fieldset>

      {/* KHUNG DÆ¯á»šI: CLAN GAMES LOG */}
      <div className="flex-1 bg-slate-900/90 border border-slate-800 rounded-md overflow-hidden flex flex-col">
        <div className="bg-slate-950 px-2 py-1 border-b border-slate-800 text-[10px] font-mono text-slate-400 text-center">
          -------------------- Clan Games LOG --------------------
        </div>
        <ScrollArea className="flex-1 p-2 font-mono text-[10px] text-slate-400">
          <div className="italic text-slate-600">No Clan Games activity recorded yet...</div>
        </ScrollArea>
      </div>

      {/* POPUP MODAL: CLANGAMES CHALLENGE SETTINGS (Full 11 Categories TreeView) */}
      {showSettingsModal && (
        <div className="absolute inset-0 z-50 bg-slate-950/85 backdrop-blur-[1px] flex items-center justify-center p-1.5">
          <div className="w-full h-full max-h-[385px] bg-slate-900 border border-slate-700 rounded-lg shadow-2xl flex flex-col p-2.5 text-[10px]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1 mb-2">
              <span className="font-bold text-xs text-slate-100">
                ClanGames Challenge Settings
              </span>
              <span className="text-[10px] text-emerald-400 font-mono">
                {Object.values(selectedChallenges).filter(Boolean).length} selected
              </span>
            </div>

            <div className="flex-1 grid grid-cols-12 gap-2.5 overflow-hidden">
              {/* Cá»˜T TRÃI (6 cá»™t): CÃ‚Y THÆ¯ Má»¤C NHIá»†M Vá»¤ */}
              <div className="col-span-6 bg-slate-950 border border-slate-800 rounded overflow-hidden flex flex-col">
                <ScrollArea className="flex-1 p-1.5">
                  <div className="flex flex-col gap-0.5">
                    {CLAN_GAMES_TREE.map((cat) => {
                      const isExpanded = !!expandedCats[cat.id];
                      const catChecked = isCategoryChecked(cat);
                      return (
                        <div key={cat.id} className="select-none">
                          {/* DÃ²ng Category cha */}
                          <div className="flex items-center gap-1 py-0.5 px-1 rounded hover:bg-slate-900">
                            <button
                              type="button"
                              onClick={() => toggleExpand(cat.id)}
                              className="w-3.5 h-3.5 flex items-center justify-center text-slate-400 hover:text-white border border-slate-700 rounded-[2px] bg-slate-900"
                            >
                              {isExpanded ? (
                                <ChevronDown className="w-2.5 h-2.5" />
                              ) : (
                                <ChevronRight className="w-2.5 h-2.5" />
                              )}
                            </button>
                            <Checkbox
                              checked={catChecked}
                              onCheckedChange={(v) => toggleCategory(cat, v as boolean)}
                              className="h-3 w-3 border-slate-600 data-[state=checked]:bg-emerald-600"
                            />
                            <span
                              onClick={() => toggleExpand(cat.id)}
                              className="font-semibold text-slate-200 cursor-pointer truncate"
                            >
                              {cat.label}
                            </span>
                          </div>

                          {/* CÃ¡c má»¥c con */}
                          {isExpanded && (
                            <div className="pl-5 border-l border-dotted border-slate-700 ml-2 flex flex-col gap-0.5 my-0.5">
                              {cat.items.map((item) => {
                                const key = `${cat.id}:${item}`;
                                const isChecked = !!selectedChallenges[key];
                                const isFocused = focusedItem === key;
                                return (
                                  <div
                                    key={key}
                                    onClick={() => setFocusedItem(key)}
                                    className={`flex items-center gap-1.5 py-0.5 px-1 rounded cursor-pointer ${
                                      isFocused ? "bg-sky-600/30 text-white" : "hover:bg-slate-900 text-slate-300"
                                    }`}
                                  >
                                    <Checkbox
                                      checked={isChecked}
                                      onCheckedChange={(v) => toggleItem(cat.id, item, v as boolean)}
                                      className="h-3 w-3 border-slate-600 data-[state=checked]:bg-emerald-600"
                                    />
                                    <span className="truncate">{item}</span>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              </div>

              {/* Cá»˜T PHáº¢I (6 cá»™t): TÃ™Y CHá»ŒN & MÃ” Táº¢ */}
              <div className="col-span-6 flex flex-col justify-between gap-1.5">
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="cg-force"
                      checked={alwaysForceAttack}
                      onCheckedChange={(v) => setAlwaysForceAttack(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="cg-force" className="text-slate-200 cursor-pointer">
                      Always Force Attack
                    </label>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="cg-purge"
                      checked={purgeUnselected}
                      onCheckedChange={(v) => setPurgeUnselected(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="cg-purge" className="text-slate-200 cursor-pointer">
                      Purge Unselected Challenges
                    </label>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Checkbox
                      id="cg-reserve"
                      checked={reservePointsPurge}
                      onCheckedChange={(v) => setReservePointsPurge(v as boolean)}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <label htmlFor="cg-reserve" className="text-slate-200 cursor-pointer">
                      Reserve Points & Purge
                    </label>
                  </div>

                  {/* Radio: All Challenges / No 1 Day Challenges */}
                  <div className="flex items-center justify-between pl-2 py-0.5">
                    <label className="flex items-center gap-1 cursor-pointer text-slate-300">
                      <input
                        type="radio"
                        name="cg-duration"
                        checked={challengeDurationFilter === "all"}
                        onChange={() => setChallengeDurationFilter("all")}
                        className="accent-emerald-500"
                      />
                      All Challenges
                    </label>
                    <label className="flex items-center gap-1 cursor-pointer text-slate-300">
                      <input
                        type="radio"
                        name="cg-duration"
                        checked={challengeDurationFilter === "no_1day"}
                        onChange={() => setChallengeDurationFilter("no_1day")}
                        className="accent-emerald-500"
                      />
                      No 1 Day Challenges
                    </label>
                  </div>

                  {/* Challenges Sorting */}
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      <Checkbox
                        id="cg-sort"
                        checked={sortingEnabled}
                        onCheckedChange={(v) => setSortingEnabled(v as boolean)}
                        className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                      />
                      <label htmlFor="cg-sort" className="text-slate-200 cursor-pointer">
                        Challenges Sorting :
                      </label>
                    </div>
                    <Select
                      disabled={!sortingEnabled}
                      value={sortingMode}
                      onValueChange={setSortingMode}
                    >
                      <SelectTrigger className="h-6 text-[10px] w-full bg-slate-950 border-slate-700 px-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                        <SelectItem value="Lower Difficulties">Lower Difficulties</SelectItem>
                        <SelectItem value="Higher Points">Higher Points</SelectItem>
                        <SelectItem value="Shorter Time">Shorter Time</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Khung Description */}
                <fieldset className="flex-1 border border-slate-800 bg-slate-950/60 rounded px-2 py-1">
                  <legend className="px-1 text-[9px] text-slate-400">Description</legend>
                  <p className="text-[10px] text-slate-300 leading-snug">
                    {focusedItem
                      ? `Selected challenge: ${focusedItem.split(":")[1]} (${focusedItem.split(":")[0].toUpperCase()})`
                      : "Click on any challenge in the list to view details."}
                  </p>
                </fieldset>

                {/* Challenges Priority Select */}
                <fieldset className="border border-slate-800 bg-slate-950/60 rounded px-2 py-1">
                  <legend className="px-1 text-[9px] text-slate-400">
                    Challenges Priority Select
                  </legend>
                  <div className="flex items-center justify-between text-[10px]">
                    <label className="flex items-center gap-1 cursor-pointer text-slate-300">
                      <input
                        type="radio"
                        name="cg-priority"
                        checked={prioritySelect === "bb"}
                        onChange={() => setPrioritySelect("bb")}
                        className="accent-emerald-500"
                      />
                      BB First
                    </label>
                    <label className="flex items-center gap-1 cursor-pointer text-slate-300">
                      <input
                        type="radio"
                        name="cg-priority"
                        checked={prioritySelect === "main"}
                        onChange={() => setPrioritySelect("main")}
                        className="accent-emerald-500"
                      />
                      Main First
                    </label>
                    <label className="flex items-center gap-1 cursor-pointer text-slate-300">
                      <input
                        type="radio"
                        name="cg-priority"
                        checked={prioritySelect === "equal"}
                        onChange={() => setPrioritySelect("equal")}
                        className="accent-emerald-500"
                      />
                      Both Equal
                    </label>
                  </div>
                </fieldset>

                <div className="flex justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => setShowSettingsModal(false)}
                    className="h-6 px-4 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-100"
                  >
                    Close
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}