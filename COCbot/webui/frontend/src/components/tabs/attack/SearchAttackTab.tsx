import React, { useState } from "react";
import {
  Shield,
  Swords,
  Settings,
  Search,
  Database,
  Coins,
  Droplet,
  Home,
} from "lucide-react";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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

// Component tái sử dụng cho cả DeadBase và ActiveBase
function BaseProfilePanel({ baseType }: { baseType: "DeadBase" | "ActiveBase" }) {
  // Search tab states[cite: 25]
  const [searchEnabled, setSearchEnabled] = useState(true);
  const [searchMin, setSearchMin] = useState("1");
  const [searchMax, setSearchMax] = useState("9999");
  const [armyCampCheck, setArmyCampCheck] = useState(false);
  const [armyCampPercent, setArmyCampPercent] = useState("80");

  const [filterMode, setFilterMode] = useState("G And E");
  const [minGold, setMinGold] = useState("80000");
  const [minElixir, setMinElixir] = useState("80000");
  const [deEnabled, setDeEnabled] = useState(false);
  const [minDe, setMinDe] = useState("0");
  const [thEnabled, setThEnabled] = useState(false);
  const [thRange, setThRange] = useState("4-6");
  const [deadEagleSearch, setDeadEagleSearch] = useState(false);
  const [deadEagleCount, setDeadEagleCount] = useState("50");
  const [meetOneAttack, setMeetOneAttack] = useState(false);

  // Weak Base Max Defense Level (8 defenses)[cite: 25]
  const [weakDefs, setWeakDefs] = useState([
    { id: "mortar", name: "Mortar", enabled: false, lvl: "Lvl 5" },
    { id: "wiz", name: "Wiz Tower", enabled: false, lvl: "Lvl 4" },
    { id: "ad", name: "Air Def", enabled: false, lvl: "Lvl 7" },
    { id: "xbow", name: "X-Bow", enabled: false, lvl: "Lvl 2" },
    { id: "scatter", name: "Scatter", enabled: false, lvl: "Lvl 1" },
    { id: "inferno", name: "Inferno", enabled: false, lvl: "Lvl 2" },
    { id: "eagle", name: "Eagle", enabled: false, lvl: "Lvl 1" },
    { id: "mono", name: "Monolith", enabled: false, lvl: "Lvl 1" },
  ]);

  // Attack tab states[cite: 26]
  const [attackMode, setAttackMode] = useState("Standard Attack");
  const [attackScript, setAttackScript] = useState("Default");
  const [dropOrderMode, setDropOrderMode] = useState("Default (All Troops)");
  const [attackOn, setAttackOn] = useState("All Sides Equally");
  const [smartRedline, setSmartRedline] = useState(true);
  const [dropType, setDropType] = useState("Sides > Troops");
  const [targetCollectors, setTargetCollectors] = useState([false, false, false]);
  const [deployTiming, setDeployTiming] = useState("1 (Fast)");

  return (
    <Tabs defaultValue="search" className="flex-1 flex flex-col overflow-hidden text-[10px]">
      <TabsList className="w-full grid grid-cols-3 bg-slate-950 border border-slate-800/80 h-6 p-0.5 mb-1.5">
        <TabsTrigger value="search" className="text-[10px] px-1 gap-1">
          <Search className="w-2.5 h-2.5 text-amber-400" /> Search
        </TabsTrigger>
        <TabsTrigger value="attack" className="text-[10px] px-1 gap-1">
          <Swords className="w-2.5 h-2.5 text-emerald-400" /> Attack
        </TabsTrigger>
        <TabsTrigger value="collectors" className="text-[10px] px-1 gap-1">
          <Database className="w-2.5 h-2.5 text-sky-400" /> Collectors
        </TabsTrigger>
      </TabsList>

      {/* SUB-TAB 1: SEARCH[cite: 25] */}
      <TabsContent value="search" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
        <div className="grid grid-cols-12 gap-1.5 h-full">
          {/* Cột trái (5 cột): Search Conditions[cite: 25] */}
          <fieldset className="col-span-5 border border-slate-800 bg-slate-900/60 rounded p-2 flex flex-col gap-2">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">
              Search Conditions
            </legend>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1">
                <Checkbox
                  checked={searchEnabled}
                  onCheckedChange={(v) => setSearchEnabled(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <span>Search</span>
              </div>
              <div className="flex items-center gap-1">
                <Input
                  value={searchMin}
                  onChange={(e) => setSearchMin(e.target.value)}
                  className="h-5 w-8 text-center font-mono bg-slate-950 border-slate-700 px-0.5"
                />
                <span>-</span>
                <Input
                  value={searchMax}
                  onChange={(e) => setSearchMax(e.target.value)}
                  className="h-5 w-11 text-center font-mono bg-slate-950 border-slate-700 px-0.5"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1">
                <Checkbox
                  checked={armyCampCheck}
                  onCheckedChange={(v) => setArmyCampCheck(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <span>Army Camps</span>
              </div>
              <div className="flex items-center gap-1">
                <span>≥</span>
                <Input
                  disabled={!armyCampCheck}
                  value={armyCampPercent}
                  onChange={(e) => setArmyCampPercent(e.target.value)}
                  className="h-5 w-9 text-center font-mono bg-slate-950 border-slate-700 px-0.5"
                />
                <span>%</span>
              </div>
            </div>

            <div className="mt-auto p-1.5 rounded bg-slate-950/70 border border-slate-800/80 text-[9px] text-slate-400">
              Active Profile: <span className="text-amber-400 font-bold">{baseType}</span>
            </div>
          </fieldset>

          {/* Cột phải (7 cột): Filters & Weak Base[cite: 25] */}
          <fieldset className="col-span-7 border border-slate-800 bg-slate-900/60 rounded p-2 flex flex-col justify-between gap-1">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">Filters</legend>

            {/* G And E + Gold/Elixir inputs[cite: 25] */}
            <div className="grid grid-cols-12 gap-1.5 items-center">
              <div className="col-span-5">
                <Select value={filterMode} onValueChange={setFilterMode}>
                  <SelectTrigger className="h-6 text-[10px] w-full bg-slate-950 border-slate-700 px-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="G And E">G And E</SelectItem>
                    <SelectItem value="G Or E">G Or E</SelectItem>
                    <SelectItem value="G + E">G + E</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-7 flex flex-col gap-1">
                <div className="flex items-center gap-1">
                  <Input
                    value={minGold}
                    onChange={(e) => setMinGold(e.target.value)}
                    className="h-5 flex-1 text-center font-mono bg-slate-950 border-slate-700 px-1"
                  />
                  <Coins className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                </div>
                <div className="flex items-center gap-1">
                  <Input
                    value={minElixir}
                    onChange={(e) => setMinElixir(e.target.value)}
                    className="h-5 flex-1 text-center font-mono bg-slate-950 border-slate-700 px-1"
                  />
                  <Droplet className="w-3.5 h-3.5 text-pink-400 shrink-0" />
                </div>
              </div>
            </div>

            {/* Dark Elixir & Town Hall[cite: 25] */}
            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  checked={deEnabled}
                  onCheckedChange={(v) => setDeEnabled(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <span>Dark Elixir</span>
              </div>
              <div className="flex items-center gap-1">
                <Input
                  disabled={!deEnabled}
                  value={minDe}
                  onChange={(e) => setMinDe(e.target.value)}
                  className="h-5 w-16 text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
                <Droplet className="w-3.5 h-3.5 text-purple-400 fill-purple-400 shrink-0" />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  checked={thEnabled}
                  onCheckedChange={(v) => setThEnabled(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <span>Town Hall</span>
              </div>
              <div className="flex items-center gap-1">
                <Select disabled={!thEnabled} value={thRange} onValueChange={setThRange}>
                  <SelectTrigger className="h-5 text-[10px] w-16 bg-slate-950 border-slate-700 px-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="4-6">4-6</SelectItem>
                    <SelectItem value="7-9">7-9</SelectItem>
                    <SelectItem value="10-12">10-12</SelectItem>
                    <SelectItem value="13-17">13-17</SelectItem>
                  </SelectContent>
                </Select>
                <Home className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  checked={deadEagleSearch}
                  onCheckedChange={(v) => setDeadEagleSearch(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <span>Dead Eagle Search</span>
              </div>
              <Input
                disabled={!deadEagleSearch}
                value={deadEagleCount}
                onChange={(e) => setDeadEagleCount(e.target.value)}
                className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <Checkbox
                checked={meetOneAttack}
                onCheckedChange={(v) => setMeetOneAttack(v as boolean)}
                className="h-3.5 w-3.5 border-slate-600"
              />
              <span>Meet One Then Attack</span>
            </div>

            {/* Weak Base | Max Defense Level (Grid 2x4)[cite: 25] */}
            <fieldset className="border border-slate-800 bg-slate-950/60 rounded p-1.5">
              <legend className="px-1 text-[9px] text-slate-400">
                Weak Base | Max Defense Level
              </legend>
              <div className="grid grid-cols-2 gap-1">
                {weakDefs.map((def, idx) => (
                  <div key={def.id} className="flex items-center gap-1">
                    <Checkbox
                      checked={def.enabled}
                      onCheckedChange={(v) => {
                        const next = [...weakDefs];
                        next[idx].enabled = v as boolean;
                        setWeakDefs(next);
                      }}
                      className="h-3 w-3 border-slate-600"
                    />
                    <Select
                      disabled={!def.enabled}
                      value={def.lvl}
                      onValueChange={(val) => {
                        const next = [...weakDefs];
                        next[idx].lvl = val;
                        setWeakDefs(next);
                      }}
                    >
                      <SelectTrigger className="h-4 text-[9px] flex-1 bg-slate-900 border-slate-700 px-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                        {["Lvl 1", "Lvl 2", "Lvl 3", "Lvl 4", "Lvl 5", "Lvl 6", "Lvl 7"].map((l) => (
                          <SelectItem key={l} value={l}>{l}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <span className="text-[8px] text-slate-400 w-9 truncate">{def.name}</span>
                  </div>
                ))}
              </div>
            </fieldset>
          </fieldset>
        </div>
      </TabsContent>

      {/* SUB-TAB 2: ATTACK[cite: 26] */}
      <TabsContent value="attack" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
        <div className="grid grid-cols-12 gap-2 h-full">
          {/* Cột trái (5 cột): Attack Mode[cite: 26] */}
          <fieldset className="col-span-5 border border-slate-800 bg-slate-900/60 rounded p-2 flex flex-col gap-2">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">Attack Mode</legend>

            <Select value={attackMode} onValueChange={setAttackMode}>
              <SelectTrigger className="h-6 text-[10px] w-full bg-slate-950 border-slate-700 px-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                <SelectItem value="Standard Attack">Standard Attack</SelectItem>
                <SelectItem value="Scripted Attack">Scripted Attack (CSV)</SelectItem>
                <SelectItem value="Smart Farm">Smart Farm</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center gap-1.5">
              <Home className="w-4 h-4 text-amber-400 shrink-0" />
              <Select value={attackScript} onValueChange={setAttackScript}>
                <SelectTrigger className="h-6 text-[10px] flex-1 bg-slate-950 border-slate-700 px-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                  <SelectItem value="Default">Default</SelectItem>
                  <SelectItem value="Barch 4 Sides">Barch 4 Sides</SelectItem>
                  <SelectItem value="Goblin Knife">Goblin Knife</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </fieldset>

          {/* Cột phải (7 cột): Deploy[cite: 26] */}
          <fieldset className="col-span-7 border border-slate-800 bg-slate-900/60 rounded p-2 flex flex-col justify-between">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">Deploy</legend>

            <div className="flex flex-col gap-2">
              <div>
                <div className="text-slate-300 mb-1">Troop Drop Order</div>
                <Select value={dropOrderMode} onValueChange={setDropOrderMode}>
                  <SelectTrigger className="h-6 text-[10px] w-full bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="Default (All Troops)">Default (All Troops)</SelectItem>
                    <SelectItem value="Custom Drop Order">Custom Drop Order</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between gap-2">
                <span>Attack On:</span>
                <Select value={attackOn} onValueChange={setAttackOn}>
                  <SelectTrigger className="h-6 text-[10px] w-[150px] bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="All Sides Equally">All Sides Equally</SelectItem>
                    <SelectItem value="Two Sides">Two Sides</SelectItem>
                    <SelectItem value="One Side">One Side</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1.5">
                <Checkbox
                  id={`redline-${baseType}`}
                  checked={smartRedline}
                  onCheckedChange={(v) => setSmartRedline(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor={`redline-${baseType}`} className="text-slate-200 cursor-pointer">
                  Use Smart Attack: Near Red Line
                </label>
              </div>

              <div className="flex items-center justify-between gap-2">
                <span>Drop Type:</span>
                <Select value={dropType} onValueChange={setDropType}>
                  <SelectTrigger className="h-6 text-[10px] w-[150px] bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="Sides > Troops">{"Sides > Troops"}</SelectItem>
                    <SelectItem value="Troops > Sides">{"Troops > Sides"}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* 3 Checkbox Target Collectors[cite: 26] */}
              <div className="flex items-center justify-center gap-4 py-1">
                {[
                  { label: "Mines", color: "text-amber-400" },
                  { label: "Pumps", color: "text-pink-400" },
                  { label: "Drills", color: "text-purple-400" },
                ].map((c, idx) => (
                  <div key={c.label} className="flex items-center gap-1">
                    <Checkbox
                      checked={targetCollectors[idx]}
                      onCheckedChange={(v) => {
                        const next = [...targetCollectors];
                        next[idx] = v as boolean;
                        setTargetCollectors(next);
                      }}
                      className="h-3.5 w-3.5 border-slate-600"
                    />
                    <span className={`font-medium ${c.color}`}>{c.label}</span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between gap-2">
                <span>Deploy Timing:</span>
                <Select value={deployTiming} onValueChange={setDeployTiming}>
                  <SelectTrigger className="h-6 text-[10px] w-[135px] bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    <SelectItem value="1 (Fast)">1 (Fast)</SelectItem>
                    <SelectItem value="3 (Normal)">3 (Normal)</SelectItem>
                    <SelectItem value="5 (Slow)">5 (Slow)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex justify-center pt-1">
              <Button
                variant="outline"
                className="h-6 px-6 text-[10px] bg-slate-950 border-slate-700 hover:bg-slate-800"
              >
                Drop Order
              </Button>
            </div>
          </fieldset>
        </div>
      </TabsContent>

      {/* SUB-TAB 3: COLLECTORS[cite: 25, 26] */}
      <TabsContent value="collectors" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded text-slate-500 data-[state=inactive]:hidden">
        Gửi ảnh tab Collectors nếu bạn muốn thiết kế phần này
      </TabsContent>
    </Tabs>
  );
}

export function SearchAttackTab() {
  const [deadBaseEnabled, setDeadBaseEnabled] = useState(true);
  const [activeBaseEnabled, setActiveBaseEnabled] = useState(true);

  return (
    <Tabs defaultValue="dead" className="h-full flex flex-col overflow-hidden text-[10px]">
      <TabsList className="w-full grid grid-cols-3 bg-slate-950 border border-slate-800 h-6 p-0.5 mb-1.5">
        <TabsTrigger value="dead" className="text-[10px] px-1 gap-1.5">
          <Shield className="w-2.5 h-2.5 text-amber-400" />
          <span>DeadBase</span>
          <Checkbox
            checked={deadBaseEnabled}
            onCheckedChange={(v) => setDeadBaseEnabled(v as boolean)}
            onClick={(e) => e.stopPropagation()}
            className="h-3 w-3 border-slate-500 data-[state=checked]:bg-emerald-600"
          />
        </TabsTrigger>
        <TabsTrigger value="active" className="text-[10px] px-1 gap-1.5">
          <Shield className="w-2.5 h-2.5 text-purple-400" />
          <span>ActiveBase</span>
          <Checkbox
            checked={activeBaseEnabled}
            onCheckedChange={(v) => setActiveBaseEnabled(v as boolean)}
            onClick={(e) => e.stopPropagation()}
            className="h-3 w-3 border-slate-500 data-[state=checked]:bg-emerald-600"
          />
        </TabsTrigger>
        <TabsTrigger value="sa_settings" className="text-[10px] px-1 gap-1">
          <Settings className="w-2.5 h-2.5 text-sky-400" /> Settings
        </TabsTrigger>
      </TabsList>

      <TabsContent value="dead" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
        <BaseProfilePanel baseType="DeadBase" />
      </TabsContent>

      <TabsContent value="active" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
        <BaseProfilePanel baseType="ActiveBase" />
      </TabsContent>

      <TabsContent value="sa_settings" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded text-slate-500 data-[state=inactive]:hidden">
        Gửi ảnh tab Settings của Search & Attack nếu bạn muốn thiết kế phần này
      </TabsContent>
    </Tabs>
  );
}