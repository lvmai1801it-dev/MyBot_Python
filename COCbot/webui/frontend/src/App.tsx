import { useState, useEffect } from "react";
import {
  Play,
  Square,
  Search,
  Camera,
  EyeOff,
  PanelLeft,
  ChevronLeft,
  ChevronRight,
  Shield,
  Terminal,
  Swords,
  Bot,
  Home,
  BarChart3,
  Info,
  Hammer,
  Gem,
  Coins,
  Droplet,
  Crown,
} from "lucide-react";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { LogTab, type LogEntry } from "@/components/tabs/LogTab";
import { VillageTab } from "@/components/tabs/VillageTab";
import { AttackPlanTab } from "@/components/tabs/AttackPlanTab";
declare global {
  interface Window {
    pywebview?: {
      api: {
        start_bot: (mode: string) => Promise<void>;
        stop_bot: () => Promise<void>;
        take_screenshot: () => Promise<void>;
        toggle_hide_emulator: () => Promise<void>;
        set_quick_preset: (preset: string) => Promise<void>;
      };
    };
    addBotLog?: (time: string, text: string, type: string) => void;
  }
}

export default function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [bgMode, setBgMode] = useState(true);
  const [activePreset, setActivePreset] = useState<string>("Direct");

  const [botLogs, setBotLogs] = useState<LogEntry[]>([
    { time: "5:16:06 PM", text: "================== BOT LOG ==================", type: "header" },
    { time: "5:16:06 PM", text: "Android Emulator MEmu", type: "default" },
    { time: "5:16:08 PM", text: "Watchdog Launched", type: "warning" },
    { time: "5:16:53 PM", text: "Android Emulator Configuration: MEmu (MEmu)", type: "success" },
    { time: "5:16:53 PM", text: "Emulator detected on your system:", type: "default" },
    { time: "5:16:53 PM", text: "  - MEmu v9.5.6.1", type: "success" },
  ]);

  useEffect(() => {
    window.addBotLog = (time: string, text: string, type: string) => {
      setBotLogs((prev) => [...prev, { time, text, type }]);
    };
  }, []);

  const heroStatuses = [
    { label: "K", name: "King", ready: true },
    { label: "Q", name: "Queen", ready: true },
    { label: "P", name: "Prince", ready: false },
    { label: "W", name: "Warden", ready: true },
    { label: "C", name: "Champion", ready: false },
    { label: "D", name: "Clan Castle", ready: true },
  ];

  const handleStartStop = () => {
    const nextState = !isRunning;
    setIsRunning(nextState);
    if (window.pywebview) {
      nextState ? window.pywebview.api.start_bot("normal") : window.pywebview.api.stop_bot();
    }
  };

  const handlePresetClick = (preset: string) => {
    setActivePreset(preset);
    window.pywebview?.api.set_quick_preset(preset);
  };

  return (
    <div className="w-screen h-screen overflow-hidden flex flex-col bg-slate-950 text-slate-100 select-none font-sans text-xs">
      {/* 1. TOP BANNER HEADER */}
      <div className="bg-gradient-to-r from-indigo-950 via-blue-900 to-slate-900 border-b border-slate-800 px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-400/40 flex items-center justify-center shadow-inner">
            <Bot className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm tracking-tight text-white">
                MyBot PH MOD
              </span>
              <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 border border-emerald-500/40 text-[10px] font-mono text-emerald-300">
                v16.5
              </span>
            </div>
            <div className="text-[10px] text-blue-200/70 font-mono">
              http://mybot.run - Freeware Bot - Opensource
            </div>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-950/60 border border-slate-700 text-emerald-400 font-mono">
            MEmu 860x732
          </span>
        </div>
      </div>

      {/* 2. Há»† THá»NG TABS CHÃNH */}
      <Tabs defaultValue="log" className="flex-1 flex flex-col overflow-hidden">
        <div className="px-2 pt-1.5 pb-1 bg-slate-900 border-b border-slate-800">
          <TabsList className="w-full grid grid-cols-6 bg-slate-950 border border-slate-800 h-8 p-0.5">
            <TabsTrigger value="log" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-amber-400">
              <Terminal className="w-3 h-3 shrink-0" /> Log
            </TabsTrigger>
            <TabsTrigger value="village" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-emerald-400">
              <Home className="w-3 h-3 shrink-0" /> Village
            </TabsTrigger>
            <TabsTrigger value="attack" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-rose-400">
              <Swords className="w-3 h-3 shrink-0" /> Attack
            </TabsTrigger>
            <TabsTrigger value="bot" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-sky-400">
              <Bot className="w-3 h-3 shrink-0" /> Bot
            </TabsTrigger>
            <TabsTrigger value="stats" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-purple-400">
              <BarChart3 className="w-3 h-3 shrink-0" /> Stats
            </TabsTrigger>
            <TabsTrigger value="about" className="text-[11px] px-1 gap-1 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-200">
              <Info className="w-3 h-3 shrink-0" /> About
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Ná»˜I DUNG Tá»ªNG TAB */}
        <div className="flex-1 flex flex-col p-2 pb-1 overflow-hidden">
          <TabsContent value="log" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
            <LogTab botLogs={botLogs} onClearLogs={() => setBotLogs([])} />
          </TabsContent>

          <TabsContent value="village" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
            <VillageTab />
          </TabsContent>

          <TabsContent value="attack" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
           <AttackPlanTab />
          </TabsContent>

          <TabsContent value="bot" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
            <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500">
              Gá»­i áº£nh tab Bot Ä‘á»ƒ thiáº¿t káº¿ ná»™i dung táº¡i Ä‘Ã¢y
            </div>
          </TabsContent>

          <TabsContent value="stats" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
            <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500">
              Gá»­i áº£nh tab Stats Ä‘á»ƒ thiáº¿t káº¿ ná»™i dung táº¡i Ä‘Ã¢y
            </div>
          </TabsContent>

          <TabsContent value="about" className="flex-1 m-0 overflow-hidden data-[state=inactive]:hidden">
            <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-md text-slate-500">
              Gá»­i áº£nh tab About Us Ä‘á»ƒ thiáº¿t káº¿ ná»™i dung táº¡i Ä‘Ã¢y
            </div>
          </TabsContent>
        </div>
      </Tabs>

      {/* 3. Báº¢NG ÄIá»€U KHIá»‚N DÆ¯á»šI CÃ™NG (Cá»‘ Ä‘á»‹nh á»Ÿ má»i tab) */}
      <div className="px-2 pb-2 pt-1">
        <div className="grid grid-cols-12 gap-2">
          {/* Cá»˜T TRÃI */}
          <div className="col-span-5 bg-slate-900/80 border border-slate-800 rounded-md p-2 flex flex-col justify-between gap-1.5">
            <div className="text-[10px] text-slate-400 font-mono -mb-0.5">https://mybot.run</div>
            
            <div className="grid grid-cols-2 gap-1">
              <Button
                onClick={handleStartStop}
                className={`h-8 px-1 text-[10px] font-bold ${
                  isRunning
                    ? "bg-rose-600 hover:bg-rose-700 text-white"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                {isRunning ? (
                  <><Square className="w-3 h-3 mr-1 fill-current shrink-0" /> Stop Bot</>
                ) : (
                  <><Play className="w-3 h-3 mr-1 fill-current shrink-0" /> Start Bot</>
                )}
              </Button>
              <Button
                variant="secondary"
                className="h-8 px-1 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200"
              >
                <Search className="w-3 h-3 mr-1 shrink-0" /> Search
              </Button>
            </div>

            <div className="grid grid-cols-3 gap-1">
              <Button
                variant="outline"
                onClick={() => window.pywebview?.api.take_screenshot()}
                className="h-6 px-0.5 text-[10px] border-slate-700 bg-slate-950 hover:bg-slate-800"
              >
                <Camera className="w-2.5 h-2.5 mr-0.5 shrink-0" /> Photo
              </Button>
              <Button
                variant="outline"
                onClick={() => window.pywebview?.api.toggle_hide_emulator()}
                className="h-6 px-0.5 text-[10px] border-slate-700 bg-slate-950 hover:bg-slate-800"
              >
                <EyeOff className="w-2.5 h-2.5 mr-0.5 shrink-0" /> Hide
              </Button>
              <Button
                variant="outline"
                className="h-6 px-0.5 text-[10px] border-slate-700 bg-slate-950 hover:bg-slate-800"
              >
                <PanelLeft className="w-2.5 h-2.5 mr-0.5 shrink-0" /> Dock
              </Button>
            </div>

            <div className="flex items-center justify-between pt-0.5">
              <div className="flex items-center space-x-1.5">
                <Checkbox
                  id="bg-mode"
                  checked={bgMode}
                  onCheckedChange={(checked) => setBgMode(checked as boolean)}
                  className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
                <label htmlFor="bg-mode" className="text-[11px] text-slate-300 cursor-pointer">
                  Background Mode
                </label>
              </div>
              <span className="text-[10px] font-mono text-slate-500">v16.5</span>
            </div>
          </div>

          {/* Cá»˜T PHáº¢I */}
          <div className="col-span-7 flex flex-col justify-between gap-1.5">
            <div className="grid grid-cols-6 gap-1 px-1">
              {heroStatuses.map((h) => (
                <div key={h.label} title={h.name} className="flex flex-col items-center justify-center">
                  <div
                    className={`w-6 h-6 rounded flex items-center justify-center border ${
                      h.ready
                        ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-400"
                        : "bg-slate-900 border-slate-700 text-slate-500"
                    }`}
                  >
                    <Shield className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-300 mt-0.5">{h.label}</span>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-12 w-5 px-0 text-slate-400 hover:text-white hover:bg-slate-800">
                <ChevronLeft className="w-4 h-4" />
              </Button>

              <div className="flex-1 bg-slate-900/90 border border-slate-800 rounded-md px-2.5 py-1.5">
                <div className="text-[10px] font-semibold text-amber-400 mb-1">
                  Village[TH0]: MyVillage
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
                  <div className="flex items-center gap-1.5">
                    <Coins className="w-3 h-3 text-amber-400 shrink-0" />
                    <span className="text-slate-200">0</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Hammer className="w-3 h-3 text-orange-400 shrink-0" />
                    <span className="text-slate-200">0/5</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Droplet className="w-3 h-3 text-pink-400 shrink-0" />
                    <span className="text-slate-200">0</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Crown className="w-3 h-3 text-yellow-500 shrink-0" />
                    <span className="text-slate-200">0</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Droplet className="w-3 h-3 text-purple-400 fill-purple-400 shrink-0" />
                    <span className="text-slate-200">0</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Gem className="w-3 h-3 text-emerald-400 shrink-0" />
                    <span className="text-slate-200">0</span>
                  </div>
                </div>
              </div>

              <Button variant="ghost" size="icon" className="h-12 w-5 px-0 text-slate-400 hover:text-white hover:bg-slate-800">
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            <div className="grid grid-cols-4 gap-1 pl-6 pr-6">
              {["Direct", "Rush", "BBSpam", "CCSpam"].map((mode) => (
                <Button
                  key={mode}
                  onClick={() => handlePresetClick(mode)}
                  className={`h-6 px-1 text-[10px] font-semibold ${
                    activePreset === mode
                      ? "bg-amber-500 hover:bg-amber-600 text-slate-950"
                      : "bg-slate-900 border border-slate-700 text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {mode}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 4. FOOTER STATUS BAR */}
      <div className="px-3 py-1 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
        <span>Status :  - MEmu v9.5.6.1</span>
        <span className="text-[10px] font-mono text-emerald-500">â— Ready</span>
      </div>
    </div>
  );
}