import { useState, useEffect } from 'react';
import axios from 'axios';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const API_BASE = 'http://localhost:8000';

function App() {
  const [view, setView] = useState('manager');
  
  return (
    <div className="min-h-screen p-4 md:p-8 font-sans">
      <header className="flex flex-col md:flex-row justify-between items-center mb-12 pb-6 border-b border-slate-200 gap-6">
        <div className="text-center md:text-left">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <span className="bg-emerald-100 text-emerald-600 p-2 rounded-lg">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>
            </span>
            Veena Stores
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-2 uppercase tracking-widest">AI Restaurant Management</p>
        </div>
        
        <div className="flex gap-2 bg-white/80 p-1.5 rounded-full border border-slate-200 backdrop-blur-md shadow-sm">
          <button 
            onClick={() => setView('manager')}
            className={`px-6 py-2 rounded-full text-sm font-semibold transition-all ${view === 'manager' ? 'bg-white text-emerald-600 shadow-sm border border-slate-200' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'}`}
          >
            Manager Dashboard
          </button>
          <button 
            onClick={() => setView('customer')}
            className={`px-6 py-2 rounded-full text-sm font-semibold transition-all ${view === 'customer' ? 'bg-white text-emerald-600 shadow-sm border border-slate-200' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'}`}
          >
            Customer Simulator
          </button>
        </div>
      </header>
      {view === 'manager' ? <ManagerDashboard /> : <CustomerSimulator />}
    </div>
  );
}

function ManagerDashboard() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/tables`);
        setTables(res.data);
      } catch (err) {
        console.error("Failed to fetch tables:", err);
      }
    };
    fetchTables();
    const interval = setInterval(fetchTables, 3000);
    return () => clearInterval(interval);
  }, []);

  const openModal = async (table) => {
    if (table.status !== 'Occupied') return;
    try {
      const res = await axios.get(`${API_BASE}/api/tables/${table.id}`);
      setTableDetails(res.data);
      setSelectedTable(table);
    } catch (err) {
      console.error("Failed to fetch table details:", err);
    }
  };

  const closeModal = () => {
    setSelectedTable(null);
    setTableDetails(null);
  };

  const handleCheckout = async () => {
    try {
      await axios.post(`${API_BASE}/api/tables/${selectedTable.id}/checkout`);
      closeModal();
      const res = await axios.get(`${API_BASE}/api/tables`);
      setTables(res.data);
    } catch (err) {
      console.error("Checkout failed:", err);
    }
  };

  const generatePDF = () => {
    if (!tableDetails) return;
    const doc = new jsPDF();
    
    doc.setFontSize(22);
    doc.setFont("helvetica", "bold");
    doc.text("VEENA STORES", 105, 20, null, null, "center");
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text("Authentic Indian Cuisine", 105, 27, null, null, "center");
    
    doc.text(`Table: ${selectedTable.id}`, 14, 40);
    doc.text(`Date: ${new Date().toLocaleString()}`, 14, 46);
    
    const tableColumn = ["Item", "Qty", "Price", "Total"];
    const tableRows = [];
    let subtotal = 0;
    
    tableDetails.orders.forEach(order => {
      const total = order.price * order.quantity;
      subtotal += total;
      tableRows.push([
        order.item_name,
        order.quantity.toString(),
        `Rs. ${order.price.toFixed(2)}`,
        `Rs. ${total.toFixed(2)}`
      ]);
    });
    
    autoTable(doc, {
      startY: 55,
      head: [tableColumn],
      body: tableRows,
      theme: 'plain',
      styles: { fontSize: 11, cellPadding: 3 },
      headStyles: { fillColor: [240, 240, 240], fontStyle: 'bold' }
    });
    
    const finalY = doc.lastAutoTable.finalY || 55;
    const gst = subtotal * 0.05;
    const finalTotal = subtotal + gst;
    
    doc.setFontSize(11);
    doc.text(`Subtotal: Rs. ${subtotal.toFixed(2)}`, 140, finalY + 10);
    doc.text(`GST (5%): Rs. ${gst.toFixed(2)}`, 140, finalY + 16);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text(`Total: Rs. ${finalTotal.toFixed(2)}`, 140, finalY + 25);
    doc.setFontSize(10);
    doc.setFont("helvetica", "italic");
    doc.text("Thank you for dining with us!", 105, finalY + 40, null, null, "center");
    doc.save(`Veena_Stores_Table_${selectedTable.id}_Bill.pdf`);
  };

  return (
    <main className="max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Live Floor Map</h2>
        <div className="flex gap-4 text-sm font-medium text-slate-500">
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span> Occupied</div>
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-slate-300"></span> Available</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
        {tables.map(table => (
          <div 
            key={table.id}
            onClick={() => openModal(table)}
            className={`p-8 rounded-2xl flex flex-col items-center justify-center cursor-pointer ${table.status === 'Occupied' ? 'glow-green' : 'glass-card'}`}
          >
            <span className={`text-4xl font-bold mb-3 ${table.status === 'Occupied' ? 'text-emerald-900' : 'text-slate-400'}`}>
              {table.id}
            </span>
            <span className={`text-xs uppercase tracking-widest font-bold px-4 py-1.5 rounded-full ${table.status === 'Occupied' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
              {table.status}
            </span>
          </div>
        ))}
      </div>

      {selectedTable && tableDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-3xl rounded-3xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 md:p-8 border-b border-slate-200 flex justify-between items-center bg-white">
              <h3 className="text-2xl font-bold text-slate-900">Table {selectedTable.id} Overview</h3>
              <button onClick={closeModal} className="text-slate-400 hover:text-slate-700 text-3xl leading-none transition-colors">&times;</button>
            </div>
            
            <div className="p-6 md:p-8 overflow-y-auto flex-1 space-y-8 bg-slate-50/50">
              <div>
                <h4 className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                  Call Transcript
                </h4>
                <div className="bg-white p-5 rounded-2xl border border-slate-200 text-sm text-slate-600 whitespace-pre-wrap font-mono h-40 overflow-y-auto shadow-inner leading-relaxed">
                  {tableDetails.transcript || "No transcript available."}
                </div>
              </div>
              
              <div>
                <h4 className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                  Itemized Bill
                </h4>
                {tableDetails.orders.length > 0 ? (
                  <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <tr>
                          <th className="px-5 py-4 font-semibold uppercase tracking-wider text-xs">Item</th>
                          <th className="px-5 py-4 font-semibold uppercase tracking-wider text-xs text-center">Qty</th>
                          <th className="px-5 py-4 font-semibold uppercase tracking-wider text-xs text-right">Price</th>
                          <th className="px-5 py-4 font-semibold uppercase tracking-wider text-xs text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {tableDetails.orders.map((o, idx) => (
                          <tr key={idx} className="hover:bg-slate-50 transition-colors">
                            <td className="px-5 py-4 text-slate-800 font-medium">{o.item_name}</td>
                            <td className="px-5 py-4 text-center text-slate-600">{o.quantity}</td>
                            <td className="px-5 py-4 text-right text-slate-600">₹{o.price}</td>
                            <td className="px-5 py-4 text-right font-bold text-slate-900">₹{o.price * o.quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-slate-500 italic text-sm">No items ordered yet.</p>
                )}
              </div>
            </div>
            
            <div className="p-6 md:p-8 border-t border-slate-200 bg-white">
              {(() => {
                const subtotal = tableDetails.orders.reduce((acc, o) => acc + (o.price * o.quantity), 0);
                const gst = subtotal * 0.05;
                const total = subtotal + gst;
                return (
                  <div className="flex flex-col md:flex-row justify-between items-end gap-6">
                    <div className="space-y-2 text-sm w-full md:w-auto bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div className="flex justify-between md:w-56 text-slate-500 font-medium">
                        <span>Subtotal:</span>
                        <span>₹{subtotal.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between md:w-56 text-slate-500 font-medium">
                        <span>GST (5%):</span>
                        <span>₹{gst.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between md:w-56 text-xl font-extrabold text-slate-900 pt-3 border-t border-slate-200 mt-3">
                        <span className="text-emerald-600">Total:</span>
                        <span>₹{total.toFixed(2)}</span>
                      </div>
                    </div>
                    
                    <div className="flex w-full md:w-auto gap-3">
                      <button 
                        onClick={generatePDF}
                        className="flex-1 md:flex-none bg-white hover:bg-slate-50 text-slate-700 font-bold py-3.5 px-6 rounded-xl transition-all shadow-sm hover:shadow border border-slate-200"
                      >
                        Print PDF
                      </button>
                      <button 
                        onClick={handleCheckout}
                        className="flex-1 md:flex-none bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 px-8 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                      >
                        Checkout
                      </button>
                    </div>
                  </div>
                )
              })()}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function CustomerSimulator() {
  const [table, setTable] = useState(1);
  const [calling, setCalling] = useState(false);

  const handleCall = async () => {
    setCalling(true);
    try {
      await axios.post(`${API_BASE}/call`, { table_number: parseInt(table) });
      alert(`Veena has been dispatched to your phone for Table ${table}!`);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || "Failed to trigger call. Check if backend is running.";
      alert(detail);
    } finally {
      setCalling(false);
    }
  };

  return (
    <main className="flex items-center justify-center min-h-[70vh]">
      <div className="glass-panel p-10 rounded-3xl max-w-md w-full flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner border border-emerald-200">
          <svg className="w-12 h-12 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
        </div>
        <h2 className="text-2xl font-extrabold text-slate-900 mb-2">Customer Device</h2>
        <p className="text-slate-500 text-sm mb-8 font-medium">Select your table and tap to summon Veena directly to your phone.</p>
        
        <div className="w-full space-y-6">
          <div>
            <label className="block text-sm font-bold text-slate-600 mb-2 text-left uppercase tracking-wider">Table Number</label>
            <select 
              value={table}
              onChange={(e) => setTable(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 appearance-none text-center transition-all cursor-pointer"
            >
              {[...Array(20)].map((_, i) => (
                <option key={i+1} value={i+1} className="bg-white text-slate-900">Table {i+1}</option>
              ))}
            </select>
          </div>
          
          <button 
            onClick={handleCall}
            disabled={calling}
            className={`w-full py-4 rounded-xl font-bold text-lg transition-all shadow-md ${calling ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200' : 'bg-emerald-600 hover:bg-emerald-700 text-white hover:shadow-lg transform hover:-translate-y-1'}`}
          >
            {calling ? "Dialing..." : "Call Waiter"}
          </button>
        </div>
      </div>
    </main>
  );
}

export default App;
