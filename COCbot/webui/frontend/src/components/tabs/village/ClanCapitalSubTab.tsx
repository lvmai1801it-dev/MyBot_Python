import { useState } from "react";
import {
  Hexagon,
  Award,
  Trophy,
  Shield,
  Sparkles,
} from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";

export function ClanCapitalSubTab() {
  // Stats
  const [collectCapitalGold, setCollectCapitalGold] = useState(false);

  // Forge / Craft Gold
  const [useGold, setUseGold] = useState(false);
  const [saveGold, setSaveGold] = useState("150000");

  const [useElixir, setUseElixir] = useState(false);
  const [saveElixir, setSaveElixir] = useState("1000");

  const [useDark, setUseDark] = useState(false);
  const [saveDark, setSaveDark] = useState("1000");

  const [useBbGold, setUseBbGold] = useState(false);
  const [saveBbGold, setSaveBbGold] = useState("1000");

  const [useBbElixir, setUseBbElixir] = useState(false);
  const [saveBbElixir, setSaveBbElixir] = useState("1000");

  const [smartUseResources, setSmartUseResources] = useState(false);
  const [forgeBuilders, setForgeBuilders] = useState("0");
  const [useGoldPassForge, setUseGoldPassForge] = useState(false);

  // Auto Upgrade Clan Capital
  const [autoUpgradeEnabled, setAutoUpgradeEnabled] = useState(false);
  const [capitalTreasury, setCapitalTreasury] = useState(false);
  const [priorArmyStuff, setPriorArmyStuff] = useState(false);
  const [ignoreDecorations, setIgnoreDecorations] = useState(false);
  const [ignoreWalls, setIgnoreWalls] = useState(false);

  return (
    <div className="h-full flex flex-col gap-1.5 overflow-hidden text-[10px]">
      {/* 1. STATS & LEAGUE */}
      <div className="grid grid-cols-12 gap-1.5">
        <fieldset className="col-span-9 border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5 flex flex-col justify-between gap-1.5">
          <legend className="px-1 text-[10px] font-semibold text-slate-400">
            Stats
          </legend>

          <div className="grid grid-cols-3 gap-2 items-center">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                <Hexagon className="w-3.5 h-3.5 text-amber-400 fill-amber-400/20" />
              </div>
              <span className="font-mono text-slate-300">---</span>
            </div>

            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
                <Award className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <span className="font-mono text-slate-300">---</span>
            </div>

            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-yellow-500/15 border border-yellow-500/30 flex items-center justify-center">
                <Trophy className="w-3.5 h-3.5 text-yellow-400" />
              </div>
              <span className="font-mono text-slate-300">---</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 pt-0.5">
            <Checkbox
              id="cc-collect-gold"
              checked={collectCapitalGold}
              onCheckedChange={(v) => setCollectCapitalGold(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label htmlFor="cc-collect-gold" className="text-slate-200 cursor-pointer">
              Collect Clan Capital Gold
            </label>
          </div>
        </fieldset>

        <fieldset className="col-span-3 border border-slate-800 bg-slate-900/60 rounded-md px-2 py-1.5 flex flex-col items-center justify-center">
          <legend className="px-1 text-[10px] font-semibold text-slate-400">
            League
          </legend>
          <div className="w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center my-0.5">
            <Shield className="w-5 h-5 text-slate-400" />
          </div>
        </fieldset>
      </div>

      {/* 2. FORGE / CRAFT GOLD */}
      <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
        <legend className="px-1 text-[10px] font-semibold text-slate-400">
          Forge/Craft Gold
        </legend>

        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mb-2">
          {/* Cá»™t trÃ¡i: Main Village Resources */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="forge-gold"
                  checked={useGold}
                  onCheckedChange={(v) => setUseGold(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="forge-gold" className="text-slate-200 cursor-pointer">
                  Use Gold
                </label>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-400">Save :</span>
                <Input
                  disabled={!useGold}
                  value={saveGold}
                  onChange={(e) => setSaveGold(e.target.value)}
                  className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="forge-elixir"
                  checked={useElixir}
                  onCheckedChange={(v) => setUseElixir(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="forge-elixir" className="text-slate-200 cursor-pointer">
                  Use Elixir
                </label>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-400">Save :</span>
                <Input
                  disabled={!useElixir}
                  value={saveElixir}
                  onChange={(e) => setSaveElixir(e.target.value)}
                  className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="forge-dark"
                  checked={useDark}
                  onCheckedChange={(v) => setUseDark(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="forge-dark" className="text-slate-200 cursor-pointer">
                  Use Dark
                </label>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-400">Save :</span>
                <Input
                  disabled={!useDark}
                  value={saveDark}
                  onChange={(e) => setSaveDark(e.target.value)}
                  className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
              </div>
            </div>
          </div>

          {/* Cá»™t pháº£i: Builder Base Resources & Smart Use */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="forge-bb-gold"
                  checked={useBbGold}
                  onCheckedChange={(v) => setUseBbGold(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="forge-bb-gold" className="text-slate-200 cursor-pointer">
                  Use BB Gold
                </label>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-400">Save :</span>
                <Input
                  disabled={!useBbGold}
                  value={saveBbGold}
                  onChange={(e) => setSaveBbGold(e.target.value)}
                  className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="forge-bb-elixir"
                  checked={useBbElixir}
                  onCheckedChange={(v) => setUseBbElixir(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="forge-bb-elixir" className="text-slate-200 cursor-pointer">
                  Use BB Elixir
                </label>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-slate-400">Save :</span>
                <Input
                  disabled={!useBbElixir}
                  value={saveBbElixir}
                  onChange={(e) => setSaveBbElixir(e.target.value)}
                  className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
              </div>
            </div>

            <div className="flex items-center gap-1.5 h-5">
              <Checkbox
                id="forge-smart"
                checked={smartUseResources}
                onCheckedChange={(v) => setSmartUseResources(v as boolean)}
                className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
              />
              <label htmlFor="forge-smart" className="text-slate-200 cursor-pointer">
                Smart Use of Resources
              </label>
            </div>
          </div>
        </div>

        {/* HÃ ng dÆ°á»›i: Builder count & Gold Pass Forge */}
        <div className="flex items-center justify-between pt-1.5 border-t border-slate-800/70">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300">Use</span>
            <Select value={forgeBuilders} onValueChange={setForgeBuilders}>
              <SelectTrigger className="h-5 text-[10px] w-11 bg-slate-950 border-slate-700 px-1.5">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                {["0", "1", "2", "3", "4", "5", "6"].map((n) => (
                  <SelectItem key={n} value={n}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-slate-300">Builder for Forge</span>
          </div>

          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <Checkbox
              id="forge-gold-pass"
              checked={useGoldPassForge}
              onCheckedChange={(v) => setUseGoldPassForge(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label htmlFor="forge-gold-pass" className="text-slate-200 cursor-pointer">
              Use Gold Pass Forge
            </label>
          </div>
        </div>
      </fieldset>

      {/* 3. AUTO UPGRADE CLAN CAPITAL */}
      <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
        <legend className="px-1 text-[10px] font-semibold text-slate-400">
          Auto Upgrade Clan Capital
        </legend>

        <div className="grid grid-cols-12 gap-y-1.5 items-center">
          <div className="col-span-4 flex items-center gap-1.5">
            <Checkbox
              id="cc-upg-enable"
              checked={autoUpgradeEnabled}
              onCheckedChange={(v) => setAutoUpgradeEnabled(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label htmlFor="cc-upg-enable" className="text-slate-100 font-medium cursor-pointer">
              Enable
            </label>
          </div>

          <div className="col-span-8 flex items-center gap-1.5">
            <Checkbox
              id="cc-upg-treasury"
              disabled={!autoUpgradeEnabled}
              checked={capitalTreasury}
              onCheckedChange={(v) => setCapitalTreasury(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label
              htmlFor="cc-upg-treasury"
              className={`cursor-pointer ${autoUpgradeEnabled ? "text-slate-200" : "text-slate-500"}`}
            >
              Capital Treasury
            </label>
          </div>

          <div className="col-span-4 flex items-center gap-1.5">
            <Checkbox
              id="cc-upg-army"
              disabled={!autoUpgradeEnabled}
              checked={priorArmyStuff}
              onCheckedChange={(v) => setPriorArmyStuff(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label
              htmlFor="cc-upg-army"
              className={`cursor-pointer ${autoUpgradeEnabled ? "text-slate-200" : "text-slate-500"}`}
            >
              Prior Army Stuff
            </label>
          </div>

          <div className="col-span-5 flex items-center gap-1.5">
            <Checkbox
              id="cc-upg-deco"
              disabled={!autoUpgradeEnabled}
              checked={ignoreDecorations}
              onCheckedChange={(v) => setIgnoreDecorations(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label
              htmlFor="cc-upg-deco"
              className={`cursor-pointer ${autoUpgradeEnabled ? "text-slate-200" : "text-slate-500"}`}
            >
              Ignore Decoration Buildings
            </label>
          </div>

          <div className="col-span-3 flex items-center gap-1.5 justify-end">
            <Checkbox
              id="cc-upg-walls"
              disabled={!autoUpgradeEnabled}
              checked={ignoreWalls}
              onCheckedChange={(v) => setIgnoreWalls(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label
              htmlFor="cc-upg-walls"
              className={`cursor-pointer ${autoUpgradeEnabled ? "text-slate-200" : "text-slate-500"}`}
            >
              Ignore Walls
            </label>
          </div>
        </div>
      </fieldset>

      {/* 4. CLAN CAPITAL UPGRADE LOG */}
      <div className="flex-1 bg-slate-900/90 border border-slate-800 rounded-md overflow-hidden flex flex-col">
        <div className="bg-slate-950 px-2 py-1 border-b border-slate-800 text-[10px] font-mono text-slate-400 text-center">
          ---------------- CLAN CAPITAL UPGRADE LOG ----------------
        </div>
        <ScrollArea className="flex-1 p-2 font-mono text-[10px] text-slate-400">
          <div className="italic text-slate-600">No Clan Capital upgrade activity yet...</div>
        </ScrollArea>
      </div>
    </div>
  );
}