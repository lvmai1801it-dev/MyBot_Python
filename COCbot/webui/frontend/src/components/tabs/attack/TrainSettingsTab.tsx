import React, { useState } from "react";
import { Timer, Sparkles } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";

export function TrainSettingsTab() {
  // Breaker[cite: 24]
  const [closingSettings, setClosingSettings] = useState(true);
  const [minAttacks, setMinAttacks] = useState("2");
  const [maxAttacks, setMaxAttacks] = useState("4");
  const [closeTimeMin, setCloseTimeMin] = useState("20");
  const [closeTimeMax, setCloseTimeMax] = useState("35");
  const [closeEmulator, setCloseEmulator] = useState(false);
  const [suspendPc, setSuspendPc] = useState(false);

  // Training Random Delay & Click Timing[cite: 24]
  const [addRandomDelay, setAddRandomDelay] = useState(true);
  const [delayMin, setDelayMin] = useState("5");
  const [delayMax, setDelayMax] = useState("60");
  const [clickTiming, setClickTiming] = useState([100]);

  // CC Spam & Direct Attack[cite: 24]
  const [ccMinDelay, setCcMinDelay] = useState("30");
  const [ccMaxDelay, setCcMaxDelay] = useState("60");
  const [directAttackTarget, setDirectAttackTarget] = useState<"dead" | "active">("active");

  // Boost Super Troops[cite: 24]
  const [enableSuperTroops, setEnableSuperTroops] = useState(false);
  const [skipBoostOnHalt, setSkipBoostOnHalt] = useState(false);
  const [usePotionFirst, setUsePotionFirst] = useState(false);
  const [superSlot1, setSuperSlot1] = useState("Disabled");
  const [superSlot2, setSuperSlot2] = useState("Disabled");

  // Attack Cycles, Event & Ranked[cite: 24]
  const [cycleAttacks, setCycleAttacks] = useState("3");
  const [cycleMinDelay, setCycleMinDelay] = useState("30");
  const [cycleMaxDelay, setCycleMaxDelay] = useState("60");
  const [eventOption, setEventOption] = useState<"off" | "resources" | "troops">("resources");
  const [enableRanked, setEnableRanked] = useState(false);
  const [enableRevenge, setEnableRevenge] = useState(false);
  const [waitCcTroops, setWaitCcTroops] = useState(false);

  return (
    <ScrollArea className="h-full pr-1.5 text-[10px]">
      <div className="flex flex-col gap-1.5 pb-1">
        {/* HÀNG 1: BREAKER (TRÁI) + DELAYS / CC SPAM / DIRECT ATTACK (PHẢI)[cite: 24] */}
        <div className="grid grid-cols-12 gap-1.5">
          {/* Breaker[cite: 24] */}
          <fieldset className="col-span-5 border border-slate-800 bg-slate-900/60 rounded p-2 flex flex-col justify-between gap-1.5">
            <legend className="px-1 text-[10px] font-semibold text-slate-400">Breaker</legend>

            <div className="flex items-center gap-1.5">
              <Checkbox
                id="brk-close"
                checked={closingSettings}
                onCheckedChange={(v) => setClosingSettings(v as boolean)}
                className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
              />
              <label htmlFor="brk-close" className="text-slate-200 cursor-pointer">
                Closing Settings
              </label>
            </div>

            <div>
              <div className="text-slate-300 mb-1">Consecutive Attack Limits:</div>
              <div className="flex items-center justify-center gap-1.5 font-mono">
                <Input
                  value={minAttacks}
                  onChange={(e) => setMinAttacks(e.target.value)}
                  className="h-5 w-10 text-center bg-emerald-700/80 border-emerald-500 text-white font-bold px-1"
                />
                <span className="text-slate-400">{"->"}</span>
                <Input
                  value={maxAttacks}
                  onChange={(e) => setMaxAttacks(e.target.value)}
                  className="h-5 w-10 text-center bg-emerald-700/80 border-emerald-500 text-white font-bold px-1"
                />
              </div>
            </div>

            <div>
              <div className="text-slate-300 mb-1">Random Closing Time:</div>
              <div className="flex items-center gap-1">
                <span>{">"}</span>
                <Select value={closeTimeMin} onValueChange={setCloseTimeMin}>
                  <SelectTrigger className="h-5 text-[10px] w-12 bg-slate-950 border-slate-700 px-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    {["10", "15", "20", "25", "30"].map((v) => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <span>To</span>
                <Select value={closeTimeMax} onValueChange={setCloseTimeMax}>
                  <SelectTrigger className="h-5 text-[10px] w-12 bg-slate-950 border-slate-700 px-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                    {["25", "30", "35", "45", "60"].map((v) => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <span>min.</span>
              </div>
            </div>

            <div className="flex flex-col gap-1 pt-0.5">
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="brk-emu"
                  checked={closeEmulator}
                  onCheckedChange={(v) => setCloseEmulator(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <label htmlFor="brk-emu" className="text-slate-200 cursor-pointer">
                  Close Emulator
                </label>
              </div>
              <div className="flex items-center gap-1.5">
                <Checkbox
                  id="brk-pc"
                  checked={suspendPc}
                  onCheckedChange={(v) => setSuspendPc(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600"
                />
                <label htmlFor="brk-pc" className="text-slate-200 cursor-pointer">
                  Suspend Computer
                </label>
              </div>
            </div>
          </fieldset>

          {/* Cột phải (7 cột)[cite: 24] */}
          <div className="col-span-7 flex flex-col gap-1.5">
            {/* Training Random Delay[cite: 24] */}
            <fieldset className="border border-slate-800 bg-slate-900/60 rounded p-2">
              <legend className="px-1 text-[10px] font-semibold text-slate-400">
                Training Random Delay
              </legend>
              <div className="flex items-center gap-2 mb-1.5">
                <Timer className="w-4 h-4 text-rose-400" />
                <Checkbox
                  id="rnd-delay"
                  checked={addRandomDelay}
                  onCheckedChange={(v) => setAddRandomDelay(v as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="rnd-delay" className="text-slate-200 cursor-pointer">
                  Add Random Delay
                </label>
              </div>
              <div className="flex items-center justify-center gap-1.5">
                <span>Between</span>
                <Input
                  value={delayMin}
                  onChange={(e) => setDelayMin(e.target.value)}
                  className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
                <span>and</span>
                <Input
                  value={delayMax}
                  onChange={(e) => setDelayMax(e.target.value)}
                  className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
                />
                <span>sec.</span>
              </div>
            </fieldset>

            {/* Train Click Timing[cite: 24] */}
            <fieldset className="border border-slate-800 bg-slate-900/60 rounded p-2">
              <legend className="px-1 text-[10px] font-semibold text-slate-400">
                Train Click Timing
              </legend>
              <div className="flex items-center gap-3">
                <div className="font-mono text-slate-300 w-16">
                  <div>delay</div>
                  <div className="text-amber-400 font-bold">{clickTiming[0]} ms</div>
                </div>
                <Slider
                  value={clickTiming}
                  onValueChange={setClickTiming}
                  min={20}
                  max={500}
                  step={10}
                  className="flex-1"
                />
              </div>
            </fieldset>

            {/* CC Spam Control & Direct Attack[cite: 24] */}
            <div className="grid grid-cols-2 gap-1.5">
              <fieldset className="border border-slate-800 bg-slate-900/60 rounded p-1.5">
                <legend className="px-1 text-[9px] font-semibold text-slate-400">
                  CC Spam Control
                </legend>
                <div className="flex items-center justify-between mb-1">
                  <span>Min Delay:</span>
                  <Input
                    value={ccMinDelay}
                    onChange={(e) => setCcMinDelay(e.target.value)}
                    className="h-5 w-11 text-center font-mono bg-slate-950 border-slate-700 px-1"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span>Max Delay:</span>
                  <Input
                    value={ccMaxDelay}
                    onChange={(e) => setCcMaxDelay(e.target.value)}
                    className="h-5 w-11 text-center font-mono bg-slate-950 border-slate-700 px-1"
                  />
                </div>
              </fieldset>

              <fieldset className="border border-slate-800 bg-slate-900/60 rounded p-1.5 flex flex-col justify-center gap-1.5">
                <legend className="px-1 text-[9px] font-semibold text-slate-400">
                  Direct Attack
                </legend>
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-200">
                  <input
                    type="radio"
                    name="direct-target"
                    checked={directAttackTarget === "dead"}
                    onChange={() => setDirectAttackTarget("dead")}
                    className="accent-emerald-500"
                  />
                  Dead Base
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-200">
                  <input
                    type="radio"
                    name="direct-target"
                    checked={directAttackTarget === "active"}
                    onChange={() => setDirectAttackTarget("active")}
                    className="accent-emerald-500"
                  />
                  Active Base
                </label>
              </fieldset>
            </div>
          </div>
        </div>

        {/* HÀNG 2: BOOST SUPER TROOPS[cite: 24] */}
        <fieldset className="border border-slate-800 bg-slate-900/60 rounded p-2">
          <legend className="px-1 text-[10px] font-semibold text-slate-400">
            Boost Super Troops
          </legend>
          <div className="grid grid-cols-2 gap-2 mb-1.5">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <Checkbox
                id="boost-super"
                checked={enableSuperTroops}
                onCheckedChange={(v) => setEnableSuperTroops(v as boolean)}
                className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
              />
              <label htmlFor="boost-super" className="text-slate-200 cursor-pointer">
                Enable Super Troops
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Checkbox
                  disabled={!enableSuperTroops}
                  checked={skipBoostOnHalt}
                  onCheckedChange={(v) => setSkipBoostOnHalt(v as boolean)}
                  className="h-3 w-3 border-slate-600"
                />
                <span className="text-slate-300 text-[9px]">Skip Boost On Halt</span>
              </div>
              <div className="flex items-center gap-1">
                <Checkbox
                  disabled={!enableSuperTroops}
                  checked={usePotionFirst}
                  onCheckedChange={(v) => setUsePotionFirst(v as boolean)}
                  className="h-3 w-3 border-slate-600"
                />
                <span className="text-slate-300 text-[9px]">Use Potion First</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "1:", val: superSlot1, setVal: setSuperSlot1 },
              { label: "2:", val: superSlot2, setVal: setSuperSlot2 },
            ].map((slot) => (
              <div key={slot.label} className="flex items-center gap-1.5">
                <span className="text-slate-400 font-mono">{slot.label}</span>
                <Select disabled={!enableSuperTroops} value={slot.val} onValueChange={slot.setVal}>
                  <SelectTrigger className="h-5 text-[10px] flex-1 bg-slate-950 border-slate-700 px-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                    <SelectItem value="Disabled">Disabled</SelectItem>
                    <SelectItem value="Sneaky Goblin">Sneaky Goblin</SelectItem>
                    <SelectItem value="Super Barbarian">Super Barbarian</SelectItem>
                    <SelectItem value="Super Wall Breaker">Super Wall Breaker</SelectItem>
                    <SelectItem value="Super Dragon">Super Dragon</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </fieldset>

        {/* HÀNG 3: ATTACK CYCLES | EVENT OPTIONS | RANKED/REVENGE[cite: 24] */}
        <div className="grid grid-cols-12 gap-1.5">
          <fieldset className="col-span-4 border border-slate-800 bg-slate-900/60 rounded p-1.5 flex flex-col gap-1">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">Attack Cycles</legend>
            <div className="flex items-center justify-between">
              <span>Attacks:</span>
              <Input
                value={cycleAttacks}
                onChange={(e) => setCycleAttacks(e.target.value)}
                className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
              />
            </div>
            <div className="flex items-center justify-between">
              <span>Min Delay:</span>
              <Input
                value={cycleMinDelay}
                onChange={(e) => setCycleMinDelay(e.target.value)}
                className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
              />
            </div>
            <div className="flex items-center justify-between">
              <span>Max Delay:</span>
              <Input
                value={cycleMaxDelay}
                onChange={(e) => setCycleMaxDelay(e.target.value)}
                className="h-5 w-10 text-center font-mono bg-slate-950 border-slate-700 px-1"
              />
            </div>
          </fieldset>

          <fieldset className="col-span-3 border border-slate-800 bg-slate-900/60 rounded p-1.5 flex flex-col justify-between">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">Event Options</legend>
            {[
              { id: "off", label: "Off" },
              { id: "resources", label: "Resources" },
              { id: "troops", label: "Event Troops" },
            ].map((opt) => (
              <label key={opt.id} className="flex items-center gap-1 cursor-pointer text-slate-200">
                <input
                  type="radio"
                  name="event-opt"
                  checked={eventOption === opt.id}
                  onChange={() => setEventOption(opt.id as "off" | "resources" | "troops")}
                  className="accent-emerald-500"
                />
                <span className="truncate">{opt.label}</span>
              </label>
            ))}
          </fieldset>

          <fieldset className="col-span-5 border border-slate-800 bg-slate-900/60 rounded p-1.5 flex flex-col justify-between">
            <legend className="px-1 text-[9px] font-semibold text-slate-400">
              Ranked/Revenge Battle
            </legend>
            <div className="flex items-center gap-1.5">
              <Checkbox
                id="chk-ranked"
                checked={enableRanked}
                onCheckedChange={(v) => setEnableRanked(v as boolean)}
                className="h-3 w-3 border-slate-600"
              />
              <label htmlFor="chk-ranked" className="text-slate-200 cursor-pointer truncate">
                Enable Ranked Battle
              </label>
            </div>
            <div className="flex items-center gap-1.5">
              <Checkbox
                id="chk-revenge"
                checked={enableRevenge}
                onCheckedChange={(v) => setEnableRevenge(v as boolean)}
                className="h-3 w-3 border-slate-600"
              />
              <label htmlFor="chk-revenge" className="text-slate-200 cursor-pointer truncate">
                Enable Revenge Battle
              </label>
            </div>
            <div className="flex items-center gap-1.5">
              <Checkbox
                id="chk-wait-cc"
                checked={waitCcTroops}
                onCheckedChange={(v) => setWaitCcTroops(v as boolean)}
                className="h-3 w-3 border-slate-600"
              />
              <label htmlFor="chk-wait-cc" className="text-slate-200 cursor-pointer truncate">
                Wait For Clan Castle Troops
              </label>
            </div>
          </fieldset>
        </div>
      </div>
    </ScrollArea>
  );
}