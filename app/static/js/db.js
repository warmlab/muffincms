var db;

window.indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;
if (!window.indexedDB) {
    console.log("Your browser doesn't support a stable version of IndexedDB. Such and such feature will not be available.");
}

var dbrequest = indexedDB.open('muffin', 3);

dbrequest.onerror(err => {
    // Do something with request.errorCode!
    console.error("Database error: " + event.target.errorCode);
});

dbrequest.onsuccess(res => {
    // Do something with request.result!
    db = res.target.result;
});

dbrequest.onupgradeneeded(res => {
    // Save the IDBDatabase interface 
  var db = res.target.result;

  // Create an objectStore for this database
  var objectStore = db.createObjectStore("name", { keyPath: "myKey" });
})
