import { useState } from "react";
import { Shield, HandHelping, Clock } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { RequestTroopsTab } from "./clan-castle/RequestTroopsTab";
import { DonateTroopsTab } from "./clan-castle/DonateTroopsTab";

export function ClanCastleSubTab() {
  const [donateMasterEnabled, setDonateMasterEnabled] = useState(true);

  return (
    <div className="flex-1 flex flex-col overflow-hidden h-full text-[10px]">
      <Tabs defaultValue="request" className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="w-full grid grid-cols-3 bg-slate-950 border border-slate-800/80 h-6 p-0.5 mb-1.5">
          <TabsTrigger value="request" className="text-[10px] px-1 gap-1">
            <Shield className="w-2.5 h-2.5 text-sky-400 shrink-0" /> Request Troops
          </TabsTrigger>
          <TabsTrigger value="donate" className="text-[10px] px-1 gap-1.5">
            <HandHelping className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
            <span>Donate Troops</span>
            <Checkbox
              checked={donateMasterEnabled}
              onCheckedChange={(v) => setDonateMasterEnabled(v as boolean)}
              onClick={(e) => e.stopPropagation()}
              className="h-3 w-3 border-slate-500 data-[state=checked]:bg-emerald-600"
            />
          </TabsTrigger>
          <TabsTrigger value="schedule" className="text-[10px] px-1 gap-1">
            <Clock className="w-2.5 h-2.5 text-amber-400 shrink-0" /> Schedule Donations
          </TabsTrigger>
        </TabsList>

        <TabsContent value="request" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
          <RequestTroopsTab />
        </TabsContent>

        <TabsContent value="donate" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
          <DonateTroopsTab />
        </TabsContent>

        <TabsContent value="schedule" className="flex-1 m-0 flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500 data-[state=inactive]:hidden">
          Gá»­i áº£nh tab Schedule Donations Ä‘á»ƒ thiáº¿t káº¿ pháº§n nÃ y
        </TabsContent>
      </Tabs>
    </div>
  );
}