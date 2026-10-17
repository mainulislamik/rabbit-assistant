"""
Rabbit Memory - Long-Term Personal Knowledge Core for Imon Sir.
Provides instant retrieval of verified facts, project architectures, AdSense, and infrastructure details.
"""

from typing import List, Dict, Any
import re

PERSONAL_KNOWLEDGE_BASE = [
    {
        "category": "profile",
        "title": "ইমন স্যারের পরিচিতি ও প্রফেশনাল ব্যাকগ্রাউন্ড",
        "keywords": ["imon", "profile", "career", "job", "cv", "ইমন", "পরিচয়", "চাকরি", "বায়োডাটা"],
        "content": (
            "নাম: মাইনুল ইসলাম (ইমন স্যার)।\n"
            "বর্তমান পদবী: আইটি স্পেশালিস্ট (Shopping Zone BD, সেপ্টেম্বর ২০২৬ থেকে বর্তমান)।\n"
            "পূর্ববর্তী অভিজ্ঞতা: Asiatic 360 (সিনিয়র আইটি ও সিস্টেমস ইঞ্জিনিয়ারিং)।\n"
            "শিক্ষাগত যোগ্যতা: B.Sc in Computer Science & Engineering (B.Sc CSE)।\n"
            "প্রধান দক্ষতা: ফুল-স্ট্যাক সফটওয়্যার ডেভেলপমেন্ট (Django, Next.js, FastAPI), ক্লাউড ইনফ্রাস্ট্রাকচার, "
            "ডকার ও ভার্চুয়ালাইজেশন, অটোনোমাস এআই এজেন্টস, নেটওয়ার্কিং এবং ডাটাবেস আর্কিটেকচার।"
        )
    },
    {
        "category": "hardware",
        "title": "উবুন্টু প্রাইমারি হোস্ট ও হার্ডওয়্যার স্পেক্স",
        "keywords": ["pc", "hardware", "optiplex", "gpu", "ram", "specs", "পিসি", "হার্ডওয়্যার", "র্যাম", "গ্রাফিক্স"],
        "content": (
            "মডেল: Dell OptiPlex 7060 Tower।\n"
            "সিপিইউ: Intel Core i7-10th Gen (8 Cores, 16 Threads)।\n"
            "র্যাম: 64 GB DDR4 হাই-স্পিড মেমোরি।\n"
            "গ্রাফিক্স কার্ড: Intel Arc A770 16GB Dedicated GPU (ভিডিও রেন্ডারিং, ডিপ লার্নিং ও ভিশনের জন্য প্রস্তুত)।\n"
            "স্টোরেজ: ২.৪ টেরাবাইট হাই-স্পিড NVMe SSD (Linux Ext4)।\n"
            "অপারেটিং সিস্টেম: Ubuntu 24.04 LTS (Wayland Desktop Session)।\n"
            "নেটওয়ার্ক আইপি: 192.168.0.100 (লোকাল হোম ল্যান)।"
        )
    },
    {
        "category": "project",
        "title": "StockWhisk SaaS আর্কিটেকচার ও ক্লাউড ভিপিএস",
        "keywords": ["stockwhisk", "saas", "erp", "vps", "স্টকহুইস্ক"],
        "content": (
            "প্রজেক্ট: StockWhisk Enterprise POS & ERP SaaS।\n"
            "ভিপিএস আইপি: 163.227.239.114 (Domain: stockwhisk.com)।\n"
            "মডিউল সংখ্যা: ২৮টি ইন্ডাস্ট্রিয়াল মডিউল (Fashion, Online Commerce, Electronics, Universal, Manufacturing)।\n"
            "আর্কিটেকচার: Docker Compose প্রোডাকশন ব্যাকএন্ড (Alterations, Size charts, DemoReadOnlyMiddleware)।\n"
            "অটোমেশন: প্রতিদিন রাত ১০টায় হোয়াটসঅ্যাপ বিজনেস ডাইজেস্ট (WA 10PM digest) এবং পাবলিক এপিআই v1।"
        )
    },
    {
        "category": "project",
        "title": "TryCalc মাল্টি-ক্যালকুলেটর প্ল্যাটফর্ম ও গুগল অ্যাডসেন্স",
        "keywords": ["trycalc", "calculator", "adsense", "calchub", "ট্রাইক্যাল্ক", "ক্যালকুলেটর", "অ্যাডসেন্স"],
        "content": (
            "প্রজেক্ট: TryCalc (Calchub) ইউনিভার্সাল অনলাইন ক্যালকুলেটর হাব।\n"
            "পোর্ট ও সার্ভিস: :3001 Next.js Frontend, :8000 Python Backend, :443 Caddy SSL।\n"
            "ক্যালকুলেটর সংখ্যা: ১২টি ক্যাটাগরিতে মোট ৭২৫টি নিখুঁত ক্যালকুলেটর।\n"
            "গুগল অ্যাডসেন্স পাবলিশার আইডি: pub-2861472312283458।\n"
            "অ্যাডমিন ও ট্রাফিক রাডার: /imon (অটোমেটেড SERP Radar ক্রনজব 0 3 * * *)।"
        )
    },
    {
        "category": "project",
        "title": "AmarPDF গ্লোবাল ডকুমেন্ট ইঞ্জিন",
        "keywords": ["amarpdf", "pdf", "converter", "আমারপিডিএফ", "পিডিএফ"],
        "content": (
            "প্রজেক্ট: AmarPDF High-Speed Document Conversion Platform।\n"
            "স্ট্যাক: Caddy (:80/:443) -> Next.js (:3009) + FastAPI (:8095)।\n"
            "ফিচারস: ATS Resume Scanner, AI Summary, Office-to-PDF, SQLite WAL ভিজিটর টেলিমেট্রি (/var/telemetry)।\n"
            "মনিটাইজেশন: Google AdSense (pub-2861472312283458) উইথ ৫টি অপটিমাইজড স্লট ও ডিপ এসইও (E-E-A-T)।"
        )
    },
    {
        "category": "project",
        "title": "Arcadex ক্লাসিক গেম এমুলেশন ও ওয়েব হাব",
        "keywords": ["arcadex", "game", "emulator", "ps2", "psp", "আর্কেডেক্স", "গেম"],
        "content": (
            "প্রজেক্ট: Arcadex Game Hub (:3080 Docker, GitHub: mainulislamik/arcade-hub)।\n"
            "লাইব্রেরি: ৫,৫০০+ ভেরিফাইড ক্লাসিক গেম (১০০% ফ্রি ও আনলকড)।\n"
            "সাপোর্টেড এমুলেটর: PS2 (Play! WASM), PSP (PPSSPP), PSX, J2ME (.jar), Symbian (.sis), NES, GBA।\n"
            "স্ট্রিমিং: HTTP Range ও CHD ফরম্যাটে ক্লাউড স্ট্রিমিং।"
        )
    },
    {
        "category": "project",
        "title": "Toto Cloud ডেটাসেন্টার ও সার্ভারলেস ওএস",
        "keywords": ["toto", "totocloud", "datacenter", "proxmox", "টোটো", "ক্লাউড"],
        "content": (
            "প্রজেক্ট: Toto Cloud Enterprise Datacenter OS v4.0 (~/toto-datacenter, Port :3099, Proxmox VE :8006)।\n"
            "ফিচারস: Corosync HA ক্লাস্টার, K3s কুবারনেটিস, Serverless PaaS, S3 কমপ্লায়েন্ট স্টোরেজ, অটো-স্কেলার, "
            "vHost, ZFS ডিজাস্টার রিকভারি এবং কাস্টম ড্যাশবোর্ড।"
        )
    },
    {
        "category": "project",
        "title": "WhatsApp CRM ও রিটেইল অটো-আউটরিচ",
        "keywords": ["whatsapp", "crm", "baileys", "হোয়াটসঅ্যাপ", "সিআরএম"],
        "content": (
            "প্রজেক্ট: WhatsApp Business CRM প্ল্যাটফর্ম।\n"
            "পোর্ট ও সার্ভিস: :3050 NextJS Frontend, :8050 FastAPI Backend, :5001 Baileys Socket Engine।\n"
            "এআই গেটওয়ে: লোকাল OmniRoute (:20128)।\n"
            "মেইন নম্বর: 01613511887; অটো-আউটরিচ শিডিউলার (১৫ ও ৩০ মিনিট ইন্টারভ্যাল)। রিটেইল ও কাস্টমার এনগেজমেন্ট।"
        )
    },
    {
        "category": "project",
        "title": "Picasa 3D Portal ও ERP",
        "keywords": ["picasa", "erp", "পিকাসা"],
        "content": (
            "প্রজেক্ট: PICASA 3D Portal ও ERP Suite।\n"
            "ভিপিএস পোর্টস: :3095 (Picasa 3D Portal), :8000 (ERP Backend), :3090 (Next.js Web)।"
        )
    }
]

def search_personal_memory(query: str) -> Dict[str, Any]:
    """Semantic/Keyword search over Imon Sir's long-term personal knowledge base."""
    query_lower = query.lower()
    matches = []
    
    # Exact keyword matching
    for item in PERSONAL_KNOWLEDGE_BASE:
        score = 0
        for kw in item["keywords"]:
            if kw in query_lower:
                score += 3
        # Check title and content
        words = re.findall(r"\w+", query_lower)
        for w in words:
            if len(w) > 2 and w in item["title"].lower():
                score += 2
            if len(w) > 3 and w in item["content"].lower():
                score += 1
                
        if score > 0:
            matches.append((score, item))
            
    matches.sort(key=lambda x: x[0], reverse=True)
    
    if matches:
        top_items = [m[1] for m in matches[:3]]
        formatted_content = "\n\n---\n\n".join([f"📌 {it['title']}:\n{it['content']}" for it in top_items])
        return {
            "found": True,
            "count": len(top_items),
            "content": formatted_content
        }
        
    # If no specific match found, return summary of available domains
    all_titles = [it["title"] for it in PERSONAL_KNOWLEDGE_BASE]
    return {
        "found": False,
        "message": f"নির্দিষ্ট তথ্য পাওয়া যায়নি। তবে নিম্নোক্ত বিষয়ে মেমোরি সংরক্ষিত আছে: {', '.join(all_titles[:5])} ইত্যাদি।"
    }
