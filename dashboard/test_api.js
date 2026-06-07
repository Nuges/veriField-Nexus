const { fetchActivities } = require("./src/lib/api.ts"); // Need ts-node or just use fetch

async function test() {
  const res = await fetch("http://localhost:8000/api/v1/activities");
  const data = await res.json();
  console.log("Total:", data.total);
  console.log("Data keys:", Object.keys(data));
  console.log("Data type:", Array.isArray(data.data) ? `Array[${data.data.length}]` : typeof data.data);
}
test();
