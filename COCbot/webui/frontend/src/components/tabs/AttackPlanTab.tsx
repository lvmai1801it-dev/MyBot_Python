import React from "react";
import { Swords, Search, Target, Users, Settings } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { TrainArmyTab } from "./attack/TrainArmyTab";
import { TrainSettingsTab } from "./attack/TrainSettingsTab";
import { SearchAttackTab } from "./attack/SearchAttackTab";

export function AttackPlanTab() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden h-full text-[11px]">
      {/* TẦNG 1: Train Army | Search & Attack | Strategies[cite: 23, 25] */}
      <Tabs defaultValue="train" className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="w-full grid grid-cols-3 bg-slate-900 border border-slate-800 h-7 p-0.5 mb-1">
          <TabsTrigger value="train" className="text-[11px] px-1 gap-1">
            <Swords className="w-3 h-3 text-amber-400 shrink-0" /> Train Army
          </TabsTrigger>
          <TabsTrigger value="search_attack" className="text-[11px] px-1 gap-1">
            <Search className="w-3 h-3 text-emerald-400 shrink-0" /> Search & Attack
          </TabsTrigger>
          <TabsTrigger value="strategies" className="text-[11px] px-1 gap-1">
            <Target className="w-3 h-3 text-rose-400 shrink-0" /> Strategies
          </TabsTrigger>
        </TabsList>

        {/* NỘI DUNG TRAIN ARMY (Gồm 2 tab con: Army & Settings)[cite: 23, 24] */}
        <TabsContent value="train" className="flex-1 m-0 flex flex-col overflow-hidden data-[state=inactive]:hidden">
          <Tabs defaultValue="army" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="w-48 grid grid-cols-2 bg-slate-950 border border-slate-800/80 h-6 p-0.5 mb-1.5">
              <TabsTrigger value="army" className="text-[10px] px-1 gap-1">
                <Users className="w-2.5 h-2.5 text-amber-400" /> Army
              </TabsTrigger>
              <TabsTrigger value="settings" className="text-[10px] px-1 gap-1">
                <Settings className="w-2.5 h-2.5 text-sky-400" /> Settings
              </TabsTrigger>
            </TabsList>

            <TabsContent value="army" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
              <TrainArmyTab />
            </TabsContent>

            <TabsContent value="settings" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
              <TrainSettingsTab />
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* NỘI DUNG SEARCH & ATTACK[cite: 25, 26] */}
        <TabsContent value="search_attack" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
          <SearchAttackTab />
        </TabsContent>

        {/* NỘI DUNG STRATEGIES[cite: 23] */}
        <TabsContent value="strategies" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded text-slate-500 data-[state=inactive]:hidden">
          Gửi ảnh tab Strategies nếu bạn muốn thiết kế phần này
        </TabsContent>
      </Tabs>
    </div>
  );
}