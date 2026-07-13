import { MODULE_REGISTRY } from "./src/lib/moduleRegistry";
import * as fs from "fs";

fs.writeFileSync("module_registry.json", JSON.stringify(MODULE_REGISTRY, null, 2));
