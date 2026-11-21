import { useState } from "react";
import {
  Settings,
  Shield,
  ArrowUpCircle,
  Bell,
  Home,
  Hammer,
  Trophy,
  Landmark,
  Coins,
  Droplet,
  Castle,
  FlaskConical,
  Sparkles,
  Swords,
  Target,
  XCircle,
  Crown,
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { BuilderBaseSubTab } from "@/components/tabs/village/BuilderBaseSubTab";
import { ClanCapitalSubTab } from "./village/ClanCapitalSubTab";
import { ClanGamesSubTab } from "./village/ClanGamesSubTab";
import { ClanCastleSubTab } from "./village/ClanCastleSubTab";

export function VillageTab() {
  // State cho nhÃ³m Halt Attack
  const [haltEnabled, setHaltEnabled] = useState(true);
  const [haltAction, setHaltAction] = useState("halt_attack");
  const [haltCondition, setHaltCondition] = useState("all_full");
  const [resumeGold, setResumeGold] = useState("0");
  const [resumeElixir, setResumeElixir] = useState("0");
  const [resumeDe, setResumeDe] = useState("0");
  const [starBonus, setStarBonus] = useState(false);
  const [minGold, setMinGold] = useState("10000");
  const [minElixir, setMinElixir] = useState("25000");
  const [minDe, setMinDe] = useState("500");

  // State cho nhÃ³m Collect, Clear
  const [collectRes, setCollectRes] = useState(true);
  const [lootCartFirst, setLootCartFirst] = useState(true);
  const [colGold, setColGold] = useState("0");
  const [colElixir, setColElixir] = useState("0");
  const [colDe, setColDe] = useState("0");

  const [treasuryEnabled, setTreasuryEnabled] = useState(false);
  const [tresGold, setTresGold] = useState("1000000");
  const [tresElixir, setTresElixir] = useState("1000000");
  const [tresDe, setTresDe] = useState("1000");

  const [clearTombstone, setClearTombstone] = useState(true);
  const [removeGemBox, setRemoveGemBox] = useState(false);
  const [removeObstacle, setRemoveObstacle] = useState(false);
  const [collectAchievement, setCollectAchievement] = useState(false);

  const [collectChallenge, setCollectChallenge] = useState(false);
  const [sellExtras, setSellExtras] = useState(false);
  const [consumeSnacks, setConsumeSnacks] = useState(false);

  // 9 nÃºt Locate Manually
  const manualBuildings = [
    { id: "th", label: "TH", title: "Locate Town Hall", icon: Home, color: "text-amber-400" },
    { id: "cc", label: "CC", title: "Locate Clan Castle", icon: Castle, color: "text-sky-400" },
    { id: "lab", label: "Lab", title: "Locate Laboratory", icon: FlaskConical, color: "text-purple-400" },
    { id: "spell", label: "Spl", title: "Locate Spell Factory", icon: Sparkles, color: "text-pink-400" },
    { id: "hero", label: "Hro", title: "Locate Hero Hall", icon: Crown, color: "text-yellow-400" },
    { id: "pet", label: "Pet", title: "Locate Pet House", icon: Swords, color: "text-emerald-400" },
    { id: "smith", label: "Blk", title: "Locate Blacksmith", icon: Hammer, color: "text-orange-400" },
    { id: "set", label: "Set", title: "Set Location Target", icon: Target, color: "text-rose-500" },
    { id: "clear", label: "Clr", title: "Clear Locations", icon: XCircle, color: "text-red-500" },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden h-full text-[11px]">
      {/* Táº¦NG 1: 4 SUB-TABS (Misc, Clan Castle, Upgrade, Notify) */}
      <Tabs defaultValue="misc" className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="w-full grid grid-cols-4 bg-slate-900 border border-slate-800 h-7 p-0.5 mb-1">
          <TabsTrigger value="misc" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-sky-400">
            <Settings className="w-3 h-3 shrink-0" /> Misc
          </TabsTrigger>
          <TabsTrigger value="cc" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-amber-400">
            <Shield className="w-3 h-3 shrink-0" /> Clan Castle
          </TabsTrigger>
          <TabsTrigger value="upgrade" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-emerald-400">
            <ArrowUpCircle className="w-3 h-3 shrink-0" /> Upgrade
          </TabsTrigger>
          <TabsTrigger value="notify" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-purple-400">
            <Bell className="w-3 h-3 shrink-0" /> Notify
          </TabsTrigger>
        </TabsList>

        {/* Ná»˜I DUNG TAB MISC */}
        <TabsContent value="misc" className="flex-1 flex flex-col m-0 overflow-hidden data-[state=inactive]:hidden">
          {/* Táº¦NG 2: 4 SUB-TABS CON (Normal Village, Builder Base, Clan Games, Clan Capital) */}
          <Tabs defaultValue="normal" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="w-full grid grid-cols-4 bg-slate-950 border border-slate-800/80 h-6 p-0.5 mb-1.5">
              <TabsTrigger value="normal" className="text-[10px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100">
                <Home className="w-2.5 h-2.5 shrink-0" /> Normal Village
              </TabsTrigger>
              <TabsTrigger value="builder" className="text-[10px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100">
                <Hammer className="w-2.5 h-2.5 shrink-0" /> Builder Base
              </TabsTrigger>
              <TabsTrigger value="games" className="text-[10px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100">
                <Trophy className="w-2.5 h-2.5 shrink-0" /> Clan Games
              </TabsTrigger>
              <TabsTrigger value="capital" className="text-[10px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100">
                <Landmark className="w-2.5 h-2.5 shrink-0" /> Clan Capital
              </TabsTrigger>
            </TabsList>

            {/* Ná»˜I DUNG NORMAL VILLAGE */}
            <TabsContent value="normal" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
              <ScrollArea className="h-full pr-1.5">
                <div className="flex flex-col gap-2 pb-1">
                  
                  {/* GROUP 1: HALT ATTACK */}
                  <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
                    <legend className="px-1 text-[10px] font-semibold text-slate-400">
                      Halt Attack
                    </legend>

                    {/* HÃ ng 1: Checkbox + Dropdowns */}
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Checkbox
                        checked={haltEnabled}
                        onCheckedChange={(v) => setHaltEnabled(v as boolean)}
                        className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                      />
                      <Select value={haltAction} onValueChange={setHaltAction} disabled={!haltEnabled}>
                        <SelectTrigger className="h-6 text-[10px] w-[105px] bg-slate-950 border-slate-700 px-1.5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                          <SelectItem value="halt_attack">Halt Attack</SelectItem>
                          <SelectItem value="train_only">Train Only</SelectItem>
                        </SelectContent>
                      </Select>

                      <span className="text-[10px] text-slate-400">When...</span>

                      <Select value={haltCondition} onValueChange={setHaltCondition} disabled={!haltEnabled}>
                        <SelectTrigger className="h-6 text-[10px] flex-1 bg-slate-950 border-slate-700 px-1.5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
                          <SelectItem value="all_full">All Storages Full</SelectItem>
                          <SelectItem value="gold_elixir">Gold & Elixir Full</SelectItem>
                          <SelectItem value="gold_full">Gold Full</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* HÃ ng 2: Resume Attack < [Gold] < [Elixir] < [DE] */}
                    <div className="flex items-center justify-end gap-1 mb-1">
                      <span className="text-[10px] text-slate-300 mr-1">{"Resume Attack: <"}</span>
                      <Input
                        value={resumeGold}
                        onChange={(e) => setResumeGold(e.target.value)}
                        className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Coins className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">{"<"}</span>
                      <Input
                        value={resumeElixir}
                        onChange={(e) => setResumeElixir(e.target.value)}
                        className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-pink-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">{"<"}</span>
                      <Input
                        value={resumeDe}
                        onChange={(e) => setResumeDe(e.target.value)}
                        className="h-5 w-12 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-purple-400 fill-purple-400 shrink-0" />
                    </div>

                    {/* HÃ ng 3: When star bonus available */}
                    <div className="flex items-center justify-center gap-1.5 mb-1.5">
                      <Checkbox
                        id="star-bonus"
                        checked={starBonus}
                        onCheckedChange={(v) => setStarBonus(v as boolean)}
                        className="h-3.5 w-3.5 border-slate-600"
                      />
                      <label htmlFor="star-bonus" className="text-[10px] text-slate-300 cursor-pointer">
                        When star bonus available
                      </label>
                    </div>

                    {/* HÃ ng 4: MÃ´ táº£ & NgÆ°á»¡ng tá»‘i thiá»ƒu */}
                    <p className="text-[10px] text-slate-400 leading-tight mb-1">
                      The bot will Halt automatically when you run out of Resources. It will resume when reaching these minimal values:
                    </p>
                    <div className="flex items-center justify-end gap-1">
                      <span className="text-[10px] text-slate-400">â‰¥</span>
                      <Input
                        value={minGold}
                        onChange={(e) => setMinGold(e.target.value)}
                        className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Coins className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">â‰¥</span>
                      <Input
                        value={minElixir}
                        onChange={(e) => setMinElixir(e.target.value)}
                        className="h-5 w-14 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-pink-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">â‰¥</span>
                      <Input
                        value={minDe}
                        onChange={(e) => setMinDe(e.target.value)}
                        className="h-5 w-12 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-purple-400 fill-purple-400 shrink-0" />
                    </div>
                  </fieldset>

                  {/* GROUP 2: COLLECT, CLEAR */}
                  <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2.5 py-1.5">
                    <legend className="px-1 text-[10px] font-semibold text-slate-400">
                      Collect, Clear
                    </legend>

                    {/* Collect Resources & Loot Cart */}
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="col-res"
                          checked={collectRes}
                          onCheckedChange={(v) => setCollectRes(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                        />
                        <label htmlFor="col-res" className="text-[10px] text-slate-200 cursor-pointer">
                          Collect Resources & Loot Cart
                        </label>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="loot-first"
                          checked={lootCartFirst}
                          onCheckedChange={(v) => setLootCartFirst(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                        />
                        <label htmlFor="loot-first" className="text-[10px] text-slate-200 cursor-pointer">
                          Loot Cart First
                        </label>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-1 mb-1.5">
                      <span className="text-[10px] text-slate-400">{"<"}</span>
                      <Input
                        value={colGold}
                        onChange={(e) => setColGold(e.target.value)}
                        className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Coins className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">{"<"}</span>
                      <Input
                        value={colElixir}
                        onChange={(e) => setColElixir(e.target.value)}
                        className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-pink-400 shrink-0" />
                      <span className="text-[10px] text-slate-400">{"<"}</span>
                      <Input
                        value={colDe}
                        onChange={(e) => setColDe(e.target.value)}
                        className="h-5 w-12 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                      />
                      <Droplet className="w-3 h-3 text-purple-400 fill-purple-400 shrink-0" />
                    </div>

                    {/* Treasury */}
                    <div className="flex items-center justify-between gap-1 mb-2">
                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="treasury"
                          checked={treasuryEnabled}
                          onCheckedChange={(v) => setTreasuryEnabled(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="treasury" className="text-[10px] text-slate-200 cursor-pointer">
                          Treasury
                        </label>
                      </div>

                      <div className="flex items-center gap-1">
                        <span className="text-[10px] text-slate-400">{"<"}</span>
                        <Input
                          disabled={!treasuryEnabled}
                          value={tresGold}
                          onChange={(e) => setTresGold(e.target.value)}
                          className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                        />
                        <Coins className="w-3 h-3 text-amber-400 shrink-0" />
                        <span className="text-[10px] text-slate-400">{"<"}</span>
                        <Input
                          disabled={!treasuryEnabled}
                          value={tresElixir}
                          onChange={(e) => setTresElixir(e.target.value)}
                          className="h-5 w-16 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                        />
                        <Droplet className="w-3 h-3 text-pink-400 shrink-0" />
                        <span className="text-[10px] text-slate-400">{"<"}</span>
                        <Input
                          disabled={!treasuryEnabled}
                          value={tresDe}
                          onChange={(e) => setTresDe(e.target.value)}
                          className="h-5 w-12 text-[10px] text-center font-mono bg-slate-950 border-slate-700 px-1"
                        />
                        <Droplet className="w-3 h-3 text-purple-400 fill-purple-400 shrink-0" />
                      </div>
                    </div>

                    {/* LÆ°á»›i 2 cá»™t cÃ¡c tÃ¹y chá»n dá»n dáº¹p & nháº­n thÆ°á»Ÿng */}
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 pt-1 border-t border-slate-800/70">
                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="tombstone"
                          checked={clearTombstone}
                          onCheckedChange={(v) => setClearTombstone(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                        />
                        <label htmlFor="tombstone" className="text-[10px] text-slate-200 cursor-pointer">
                          Clear Tombstone
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="challenge"
                          checked={collectChallenge}
                          onCheckedChange={(v) => setCollectChallenge(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="challenge" className="text-[10px] text-slate-200 cursor-pointer">
                          Collect Challenge Rewards
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="gembox"
                          checked={removeGemBox}
                          onCheckedChange={(v) => setRemoveGemBox(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="gembox" className="text-[10px] text-slate-200 cursor-pointer">
                          Remove GemBox
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5 pl-4">
                        <Checkbox
                          id="sell-extras"
                          checked={sellExtras}
                          onCheckedChange={(v) => setSellExtras(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="sell-extras" className="text-[10px] text-slate-200 cursor-pointer">
                          Sell Extras
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="obstacle"
                          checked={removeObstacle}
                          onCheckedChange={(v) => setRemoveObstacle(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="obstacle" className="text-[10px] text-slate-200 cursor-pointer">
                          Remove Obstacle
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5 opacity-50">
                        <Checkbox disabled className="h-3.5 w-3.5 border-slate-700" />
                        <span className="text-[10px] text-slate-400">
                          Collect Free Magic Items
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="achievement"
                          checked={collectAchievement}
                          onCheckedChange={(v) => setCollectAchievement(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="achievement" className="text-[10px] text-slate-200 cursor-pointer">
                          Collect Achievement
                        </label>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Checkbox
                          id="snacks"
                          checked={consumeSnacks}
                          onCheckedChange={(v) => setConsumeSnacks(v as boolean)}
                          className="h-3.5 w-3.5 border-slate-600"
                        />
                        <label htmlFor="snacks" className="text-[10px] text-slate-200 cursor-pointer">
                          Consume Magic Snacks
                        </label>
                      </div>
                    </div>
                  </fieldset>

                  {/* GROUP 3: LOCATE MANUALLY (9 NÃšT) */}
                  <fieldset className="border border-slate-800 bg-slate-900/60 rounded-md px-2 py-1.5">
                    <legend className="px-1 text-[10px] font-semibold text-slate-400">
                      Locate Manually
                    </legend>
                    <div className="grid grid-cols-9 gap-1">
                      {manualBuildings.map((b) => {
                        const IconComp = b.icon;
                        return (
                          <Button
                            key={b.id}
                            variant="outline"
                            title={b.title}
                            className="h-9 px-0 flex flex-col items-center justify-center gap-0.5 bg-slate-950 border-slate-700 hover:bg-slate-800"
                          >
                            <IconComp className={`w-3.5 h-3.5 ${b.color}`} />
                            <span className="text-[9px] font-mono text-slate-300">{b.label}</span>
                          </Button>
                        );
                      })}
                    </div>
                  </fieldset>

                </div>
              </ScrollArea>
            </TabsContent>

            {/* CÃC TAB CON KHÃC Cá»¦A MISC */}
            <TabsContent value="builder" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
                <BuilderBaseSubTab />
            </TabsContent>
            <TabsContent value="games" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
              <ClanGamesSubTab />
            </TabsContent>
            <TabsContent value="capital" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
           <ClanCapitalSubTab />
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* CÃC TAB CHÃNH KHÃC Cá»¦A VILLAGE */}
        <TabsContent value="cc" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
          <ClanCastleSubTab />
        </TabsContent>
        <TabsContent value="upgrade" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
          Gá»­i áº£nh tab Upgrade Ä‘á»ƒ thiáº¿t káº¿ pháº§n nÃ y
        </TabsContent>
        <TabsContent value="notify" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
          Gá»­i áº£nh tab Notify Ä‘á»ƒ thiáº¿t káº¿ pháº§n nÃ y
        </TabsContent>
      </Tabs>
    </div>
  );
}