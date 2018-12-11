// This file contains member functions for exploration of data received from the database
// Total received data
var TotalTreasuryData = [],
    TotalHousingServicesData = [],
    TotalHousingTypeData = [],
    TotalMortalityData = [];
    TotalEducationData =[];
//Translation Tables:
// Municipality temp Container
var tempMunicContainer = {
  'Buffalo City':	1,
  'Camdeboo':	2,
  'Blue Crane Route':	3,
  'Ikwezi':	4,
  'Makana':	5,
  'Ndlambe':	6,
  'Sundays River Valley':	7,
  'Baviaans':	8,
  'Kouga':	9,
  'Kou-Kamma':	10,
  'Mbhashe':	11,
  'Mnquma':	12,
  'Great Kei':	13,
  'Amahlathi':	14,
  'Ngqushwa':	15,
  'Nkonkobe':	16,
  'Nxuba':	17,
  'Inxuba Yethemba':	18,
  'Tsolwana':	19,
  'Inkwanca':	20,
  'Lukanji':	21,
  'Intsika Yethu':	22,
  'Emalahleni':	23,
  'Engcobo':	24,
  'Sakhisizwe':	25,
  'Elundini':	26,
  'Senqu':	27,
  'Maletswai':	28,
  'Gariep':	29,
  'Ngquza Hill':	30,
  'Port St Johns':	31,
  'Nyandeni':	32,
  'Mhlontlo':	33,
  'King Sabata Dalindyebo':	34,
  'Matatiele':	35,
  'Umzimvubu':	36,
  'Mbizana':	37,
  'Ntabankulu':	38,
  'Nelson Mandela Bay':	39,
  'Letsemeng':	40,
  'Kopanong':	41,
  'Mohokare':	42,
  'Naledi':	43,
  'Masilonyana':	44,
  'Tokologo':	45,
  'Tswelopele':	46,
  'Matjhabeng':	47,
  'Nala':	48,
  'Setsoto':	49,
  'Dihlabeng':	50,
  'Nketoana':	51,
  'Maluti a Phofung':	52,
  'Phumelela':	53,
  'Mantsopa':	54,
  'Moqhaka':	55,
  'Ngwathe':	56,
  'Metsimaholo':	57,
  'Mafube':	58,
  'Mangaung':	59,
  'Ekurhuleni':	60,
  'Emfuleni':	61,
  'Midvaal':	62,
  'Lesedi':	63,
  'Mogale City':	64,
  'Randfontein':	65,
  'Westonaria':	66,
  'Merafong City':	67,
  'City of Johannesburg':	68,
  'City of Tshwane':	69,
  'eThekwini':	70,
  'Vulamehlo':	71,
  'Umdoni':	72,
  'Umzumbe':	73,
  'uMuziwabantu':	74,
  'Ezingoleni':	75,
  'Hibiscus Coast':	76,
  'uMshwathi':	77,
  'uMngeni':	78,
  'Mpofana':	79,
  'Impendle':	80,
  'The Msunduzi':	81,
  'Mkhambathini':	82,
  'Richmond':	83,
  'Emnambithi/Ladysmith':	84,
  'Indaka':	85,
  'Umtshezi':	86,
  'Okhahlamba':	87,
  'Imbabazane':	88,
  'Endumeni':	89,
  'Nqutu':	90,
  'Msinga':	91,
  'Umvoti':	92,
  'Newcastle':	93,
  'Emadlangeni':	94,
  'Dannhauser':	95,
  'eDumbe':	96,
  'uPhongolo':	97,
  'Abaqulusi':	98,
  'Nongoma':	99,
  'Ulundi':	100,
  'Umhlabuyalingana':	101,
  'Jozini':	102,
  'The Big 5 False Bay':	103,
  'Hlabisa':	104,
  'Mtubatuba':	105,
  'Mfolozi':	106,
  'uMhlathuze':	107,
  'Ntambanana':	108,
  'uMlalazi':	109,
  'Mthonjaneni':	110,
  'Nkandla':	111,
  'Mandeni':	112,
  'KwaDukuza':	113,
  'Ndwedwe':	114,
  'Maphumulo':	115,
  'Ingwe':	116,
  'Kwa Sani':	117,
  'Greater Kokstad':	118,
  'Ubuhlebezwe':	119,
  'Umzimkhulu':	120,
  'Greater Giyani':	121,
  'Greater Letaba':	122,
  'Greater Tzaneen':	123,
  'Ba-Phalaborwa':	124,
  'Maruleng':	125,
  'Musina':	126,
  'Mutale':	127,
  'Thulamela':	128,
  'Makhado':	129,
  'Blouberg':	130,
  'Aganang':	131,
  'Molemole':	132,
  'Polokwane':	133,
  'Lepele-Nkumpi':	134,
  'Thabazimbi':	135,
  'Lephalale':	136,
  'Mookgopong':	137,
  'Modimolle':	138,
  'Bela-Bela':	139,
  'Mogalakwena':	140,
  'Ephraim Mogale':	141,
  'Elias Motsoaledi':	142,
  'Makhuduthamaga':	143,
  'Fetakgomo':	144,
  'Greater Tubatse':	145,
  'Albert Luthuli':	146,
  'Msukaligwa':	147,
  'Mkhondo':	148,
  'Pixley Ka Seme':	149,
  'Lekwa':	150,
  'Dipaleseng':	151,
  'Govan Mbeki':	152,
  'Victor Khanye':	153,
  'Emalahleni':	154,
  'Steve Tshwete':	155,
  'Emakhazeni':	156,
  'Thembisile':	157,
  'Dr JS Moroka':	158,
  'Thaba Chweu':	159,
  'Mbombela':	160,
  'Umjindi':	161,
  'Nkomazi':	162,
  'Bushbuckridge':	163,
  'Moretele':	164,
  'Local Municipality of Madibeng':	165,
  'Rustenburg':	166,
  'Kgetlengrivier':	167,
  'Moses Kotane':	168,
  'Ratlou':	169,
  'Tswaing':	170,
  'Mafikeng':	171,
  'Ditsobotla':	172,
  'Ramotshere Moiloa':	173,
  'Naledi':	174,
  'Mamusa':	175,
  'Greater Taung':	176,
  'Lekwa-Teemane':	177,
  'Kagisano/Molopo':	178,
  'Ventersdorp':	179,
  'Tlokwe City Council':	180,
  'City of Matlosana':	181,
  'Maquassi Hills':	182,
  'Richtersveld':	183,
  'Nama Khoi':	184,
  'Kamiesberg':	185,
  'Hantam':	186,
  'Karoo Hoogland':	187,
  'Khï¿½i-Ma':	188,
  'Ubuntu':	189,
  'Umsombomvu':	190,
  'Emthanjeni':	191,
  'Kareeberg':	192,
  'Renosterberg':	193,
  'Thembelihle':	194,
  'Siyathemba':	195,
  'Siyancuma':	196,
  'Mier':	197,
  'Kai !Garib':	198,
  '//Khara Hais':	199,
  '!Kheis':	200,
  'Tsantsabane':	201,
  'Kgatelopele':	202,
  'Sol Plaatjie':	203,
  'Dikgatlong':	204,
  'Magareng':	205,
  'Phokwane':	206,
  'Joe Morolong':	207,
  'Ga-Segonyana':	208,
  'Gamagara':	209,
  'City of Cape Town':	210,
  'Matzikama':	211,
  'Cederberg':	212,
  'Bergrivier':	213,
  'Saldanha Bay':	214,
  'Swartland':	215,
  'Witzenberg':	216,
  'Drakenstein':	217,
  'Stellenbosch':	218,
  'Breede Valley':	219,
  'Langeberg':	220,
  'Theewaterskloof':	221,
  'Overstrand':	222,
  'Cape Agulhas':	223,
  'Swellendam':	224,
  'Kannaland':	225,
  'Hessequa':	226,
  'Mossel Bay':	227,
  'George':	228,
  'Oudtshoorn':	229,
  'Bitou':	230,
  'Knysna':	231,
  'Laingsburg':	232,
  'Prince Albert':	233,
  'Beaufort West':	234,
}
// --- Custom number formatting ---
var localConfig = {
  "decimal": ".",
  "thousands": ",",
  "grouping": [3],
  "currency": ["R", ""],
  "dateTime": "%a %b %e %X %Y",
  "date": "%m/%d/%Y",
  "time": "%H:%M:%S",
  "periods": ["AM", "PM"],
  "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  "shortDays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
  "shortMonths": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
}
customFormat = d3.locale(localConfig);
// Change D3's SI prefix to more business friendly units
//      K = thousands
//      M = millions
//      B = billions
//      T = trillion
//      P = quadrillion
//      E = quintillion
// small decimals are handled with e-n formatting.
var d3_formatPrefixes = ["e-24","e-21","e-18","e-15","e-12","e-9","e-6","e-3","","K","M","B","T","P","E","Z","Y"].map(d3_formatPrefix);
// Override d3's formatPrefix function
d3.formatPrefix = function(value, precision) {
    var i = 0;
    if (value) {
        if (value < 0) {
            value *= -1;
        }
        if (precision) {
            value = d3.round(value, d3_format_precision(value, precision));
        }
        i = 1 + Math.floor(1e-12 + Math.log(value) / Math.LN10);
        i = Math.max(-24, Math.min(24, Math.floor((i - 1) / 3) * 3));
    }
    return d3_formatPrefixes[8 + i / 3];
};
function d3_formatPrefix(d, i) {
    var k = Math.pow(10, Math.abs(8 - i) * 3);
    return {
        scale: i > 8 ? function(d) { return d / k; } : function(d) { return d * k; },
        symbol: d
    };
}
function d3_format_precision(x, p) {
    return p - (x ? Math.ceil(Math.log(x) / Math.LN10) : 1);
}

// DB Province Keys
var provinceKey = {
  'Eastern Cape' : 1,
  'Free State' : 2,
  'Gauteng' : 3,
  'KwaZulu-Natal' :4,
  'Limpopo' : 5,
  'Mpumalanga' : 6,
  'Northern Cape': 7,
  'North West': 8,
  'Western Cape' : 9
};
var keyToProvince ={
  1 : 'Eastern Cape',
  2 : 'Free State',
  3 : 'Gauteng',
  4 : 'KwaZulu-Natal',
  5 : 'Limpopo',
  6 : 'Mpumalanga',
  7 : 'Northern Cape',
  8 : 'North West',
  9 : 'Western Cape'
};
// DB Municipality Keys
var municipalityKey = {
  'Lephalale':	89,
  'Impendle':	90,
  'Sakhisizwe':	91,
  'Kgetlengrivier':	92,
  'Ingwe':	93,
  'Metsimaholo':	94,
  'Ntabankulu':	95,
  'Vulamehlo':	96,
  'Drakenstein':	97,
  'Hibiscus Coast':	98,
  'Intsika Yethu':	99,
  'Tokologo':	100,
  'Moses Kotane':	101,
  'Bergrivier':	102,
  'Matjhabeng':	103,
  'uMshwathi':	104,
  'Langeberg':	105,
  'Ndlambe':	106,
  'Ubuntu':	107,
  'Knysna':	108,
  'Lowveld':	109,
  'Ba-Phalaborwa':	110,
  'Kouga':	111,
  'Oudtshoorn':	112,
  'The Msunduzi':	113,
  'Okhahlamba':	114,
  'Diamondfields':	115,
  'eThekwini':	116,
  'Newcastle':	117,
  'Bushbuckridge':	118,
  'Khï¿½i-Ma':	119,
  'Ezingoleni':	120,
  'Ikwezi':	121,
  'Nelson Mandela Bay':	122,
  'Phokwane':	123,
  'Nokeng tsa Taemane':	124,
  'Ulundi':	125,
  'Swartland':	126,
  'Buffalo City':	127,
  'Kruger Park':	128,
  'Karoo Hoogland':	129,
  'Emalahleni':	130,
  'Dannhauser':	131,
  'Lekwa-Teemane':	132,
  'Phokwane':	133,
  'Ngquza Hill':	134,
  'Msinga':	135,
  'Kungwini':	136,
  'Dihlabeng':	137,
  'Mafikeng':	138,
  'Mfolozi':	139,
  'Namaqualand':	140,
  'Molemole':	141,
  'Nkomazi':	142,
  'Siyancuma':	143,
  'Endumeni':	144,
  'Bushbuckridge':	145,
  'Westonaria':	146,
  'Magareng':	147,
  'Swellendam':	148,
  'Pixley Ka Seme':	149,
  'Kruger Park':	150,
  'Emnambithi/Ladysmith':	151,
  'Emthanjeni':	152,
  'Masilonyana':	153,
  'Mogalakwena':	154,
  'Thulamela':	155,
  'Albert Luthuli':	156,
  'Greater Taung':	157,
  'Lekwa':	158,
  'Victor Khanye':	159,
  'Local Municipality of Madibeng':	160,
  'King Sabata Dalindyebo':	161,
  'Greater Tubatse':	162,
  'Mier':	163,
  'uPhongolo':	164,
  'Karoo Hoogland':	165,
  'Camdeboo':	166,
  'KwaDukuza':	167,
  'Amahlathi':	168,
  'Elias Motsoaledi':	169,
  'Moretele':	170,
  'Aganang':	171,
  'Renosterberg':	172,
  'Thembisile':	173,
  'Steve Tshwete':	174,
  'Gaints Castle Game Reserve':	175,
  'Kagisano/Molopo':	176,
  'Makhado':	177,
  'Witzenberg':	178,
  'Umjindi':	179,
  'Kungwini':	180,
  'Elundini':	181,
  'City of Johannesburg':	182,
  'City of Cape Town':	183,
  'Nama Khoi':	184,
  'Ndwedwe':	185,
  'Mossel Bay':	186,
  'Msukaligwa':	187,
  'Ngqushwa':	188,
  'Cape Agulhas':	189,
  'Phumelela':	190,
  'Maluti a Phofung':	191,
  'Aberdeen Plain':	192,
  'Bitou':	193,
  'Rustenburg':	194,
  'Ramotshere Moiloa':	196,
  'Mtubatuba':	197,
  'Maphumulo':	198,
  'Blouberg':	199,
  'Mbizana':	200,
  'Dikgatlong':	201,
  'Blue Crane Route':	202,
  'Mthonjaneni':	203,
  'Hlabisa':	204,
  'Baviaans':	205,
  'Laingsburg':	206,
  'Senqu':	207,
  'Merafong City':	208,
  'Inxuba Yethemba':	209,
  'Letsemeng':	210,
  'Maletswai':	211,
  'Bela-Bela':	212,
  'Umsombomvu':	213,
  'Greater Tzaneen':	214,
  'Umtshezi':	215,
  'Mpofana':	216,
  'Mantsopa':	217,
  'Naledi':	218,
  'Karoo Hoogland':	219,
  'Ephraim Mogale':	220,
  'Inkwanca':	221,
  'uMhlathuze':	222,
  'Mbombela':	223,
  'Moqhaka':	224,
  'Dr JS Moroka':	225,
  'Umvoti':	226,
  'Sundays River Valley':	227,
  'George':	228,
  'Greater Letaba':	229,
  'Mbhashe':	230,
  'Kannaland':	231,
  'Greater Giyani':	232,
  'South Cape':	233,
  'Breede Valley':	234,
  'Abaqulusi':	235,
  'Thembelihle':	236,
  'Prince Albert':	237,
  'Kamiesberg':	238,
  'Indaka':	239,
  'Cederberg':	240,
  'The Big 5 False Bay':	241,
  'Umzimkhulu':	242,
  'Umzumbe':	243,
  'Nkonkobe':	244,
  'Kwa Sani':	245,
  'Fetakgomo':	246,
  'Polokwane':	247,
  'Kalahari':	248,
  'Richtersveld':	249,
  'Mafube':	250,
  'Lukanji':	251,
  'Utrecht':	252,
  'Nyandeni':	253,
  'Greater Kokstad':	254,
  'Makana':	255,
  'Midvaal':	256,
  'Engcobo':	257,
  'Tsantsabane':	258,
  'Highlands':	259,
  'Kou-Kamma':	260,
  'Govan Mbeki':	261,
  'Mangaung':	262,
  'Ntambanana':	263,
  'Mkhomazi Wilderness Area':	264,
  'Kai !Garib':	265,
  'Jozini':	266,
  'Gariep':	267,
  'Thabazimbi':	268,
  'Setsoto':	269,
  'Nkandla':	270,
  '!Kheis':	271,
  'Matzikama':	272,
  'Benede Oranje':	273,
  'Umdoni':	274,
  'Nongoma':	275,
  'Umzimvubu':	276,
  'Ngwathe':	277,
  'Stellenbosch':	278,
  'Matatiele':	279,
  'Mhlontlo':	280,
  'Merafong City':	281,
  'Maruleng':	282,
  'Imbabazane':	283,
  'Nxuba':	284,
  'Theewaterskloof':	285,
  'Siyathemba':	286,
  'Tlokwe City Council':	287,
  'City of Tshwane':	288,
  'Emalahleni':	289,
  'Thaba Chweu':	290,
  'Sol Plaatjie':	292,
  'Musina':	293,
  'uMlalazi':	294,
  'Ubuhlebezwe':	295,
  'Tsolwana':	296,
  'West Rand':	299,
  'Hantam':	300,
  'Richmond':	301,
  'Ga-Segonyana':	302,
  'eNdondakusuka':	303,
  'Nketoana':	304,
  'Mnquma':	305,
  'Port St Johns':	306,
  'Overstrand':	307,
  'uMuziwabantu':	308,
  'Makhuduthamaga':	309,
  'Great Kei':	310,
  'Kareeberg':	311,
  'Greater Tubatse':	312,
  'Ga-Segonyana':	313,
  'Ventersdorp':	314,
  'Mkhambathini':	315,
  'Joe Morolong':	316,
  'City of Matlosana':	317,
  'Modimolle':	318,
  'uMngeni':	319,
  'Kgatelopele':	320,
  'Umhlabuyalingana':	321,
  'Randfontein':	322,
  'Lepele-Nkumpi':	323,
  'Tswaing':	324,
  'Mkhondo':	325,
  'Mutale':	326,
  'Ephraim Mogale':	327,
  'Gamagara':	328,
  'Emfuleni':	329,
  'Mohokare':	330,
  'Ditsobotla':	331,
  'City of Tshwane':	332,
  'Tswelopele':	333,
  'Saldanha Bay':	334,
  'Mamusa':	335,
  'Mookgopong':	336,
  'Setla-Kgobi':	337,
  'Dipaleseng':	339,
  'Beaufort West':	340,
  'Nala':	341,
  'Maquassi Hills':	342,
  'St Lucia Park':	343,
  'Mogale City':	344,
  '//Khara Hais':	345,
  'Ekurhuleni':	346,
  'Lesedi':	347,
  'Elias Motsoaledi':	348,
  'Kopanong':	349,
  'eDumbe':	350,
  'Nqutu':	351,
  'Mountain Zebra National Park':	352,
  'Oviston Nature Reserve':	353,
  'Golden Gate Highlands National Park':	354,
  'NULL':	355,
  'Highmoor/Kamberg Park':	356,
  'NULL':	357,
  'NULL':	358,
  'Pilansberg National Park':	359,
  'Overberg':	360,
  "O'Conners Camp":	361,
  'Schuinsdraai Nature Reserve':	362,
  'Mdala Nature Reserve':	363,
};
var keyToMunicipality = {
  89:	'Lephalale',
  90:	'Impendle',
  91:	'Sakhisizwe',
  92:	'Kgetlengrivier',
  93:	'Ingwe',
  94:	'Metsimaholo',
  95:	'Ntabankulu',
  96:	'Vulamehlo',
  97:	'Drakenstein',
  98:	'Hibiscus Coast',
  99:	'Intsika Yethu',
  100:	'Tokologo',
  101:	'Moses Kotane',
  102:	'Bergrivier',
  103:	'Matjhabeng',
  104:	'uMshwathi',
  105:	'Langeberg',
  106:	'Ndlambe',
  107:	'Ubuntu',
  108:	'Knysna',
  109:	'Kouga',
  110:	'Ba-Phalaborwa',
  111:	'Kouga',
  112:	'Oudtshoorn',
  113:	'The Msunduzi',
  114:	'Okhahlamba',
  115:	'Diamondfields',
  116:	'eThekwini',
  117:	'Newcastle',
  118:	'Bushbuckridge',
  119:	'Khï¿½i-Ma',
  120:	'Ezingoleni',
  121:	'Ikwezi',
  122:	'Nelson Mandela Bay',
  123:	'Phokwane',
  124:	'Nokeng tsa Taemane',
  125:	'Ulundi',
  126:	'Swartland',
  127:	'Buffalo City',
  128:	'Kruger Park',
  129:	'Karoo Hoogland',
  130:	'Emalahleni',
  131:	'Dannhauser',
  132:	'Lekwa-Teemane',
  133:	'Phokwane',
  134:	'Ngquza Hill',
  135:	'Msinga',
  136:	'Kungwini',
  137:	'Dihlabeng',
  138:	'Mafikeng',
  139:	'Mfolozi',
  140:	'Namaqualand',
  141:	'Molemole',
  142:	'Nkomazi',
  143:	'Siyancuma',
  144:	'Endumeni',
  145:	'Bushbuckridge',
  146:	'Westonaria',
  147:	'Magareng',
  148:	'Swellendam',
  149:	'Pixley Ka Seme',
  150:	'Kruger Park',
  151:	'Emnambithi/Ladysmith',
  152:	'Emthanjeni',
  153:	'Masilonyana',
  154:	'Mogalakwena',
  155:	'Thulamela',
  156:	'Albert Luthuli',
  157:	'Greater Taung',
  158:	'Lekwa',
  159:	'Victor Khanye',
  160:	'Local Municipality of Madibeng',
  161:	'King Sabata Dalindyebo',
  162:	'Greater Tubatse',
  163:	'Mier',
  164:	'uPhongolo',
  165:	'Karoo Hoogland',
  166:	'Camdeboo',
  167:	'KwaDukuza',
  168:	'Amahlathi',
  169:	'Elias Motsoaledi',
  170:	'Moretele',
  171:	'Aganang',
  172:	'Renosterberg',
  173:	'Thembisile',
  174:	'Steve Tshwete',
  175:	'Gaints Castle Game Reserve',
  176:	'Kagisano/Molopo',
  177:	'Makhado',
  178:	'Witzenberg',
  179:	'Umjindi',
  180:	'Kungwini',
  181:	'Elundini',
  182:	'City of Johannesburg',
  183:	'City of Cape Town',
  184:	'Nama Khoi',
  185:	'Ndwedwe',
  186:	'Mossel Bay',
  187:	'Msukaligwa',
  188:	'Ngqushwa',
  189:	'Cape Agulhas',
  190:	'Phumelela',
  191:	'Maluti a Phofung',
  192:	'Aberdeen Plain',
  193:	'Bitou',
  194:	'Rustenburg',
  195:	'Hibiscus Coast',
  196:	'Ramotshere Moiloa',
  197:	'Mtubatuba',
  198:	'Maphumulo',
  199:	'Blouberg',
  200:	'Mbizana',
  201:	'Dikgatlong',
  202:	'Blue Crane Route',
  203:	'Mthonjaneni',
  204:	'Hlabisa',
  205:	'Baviaans',
  206:	'Laingsburg',
  207:	'Senqu',
  208:	'Merafong City',
  209:	'Inxuba Yethemba',
  210:	'Letsemeng',
  211:	'Maletswai',
  212:	'Bela-Bela',
  213:	'Umsombomvu',
  214:	'Greater Tzaneen',
  215:	'Umtshezi',
  216:	'Mpofana',
  217:	'Mantsopa',
  218:	'Naledi',
  219:	'Karoo Hoogland',
  220:	'Ephraim Mogale',
  221:	'Inkwanca',
  222:	'uMhlathuze',
  223:	'Mbombela',
  224:	'Moqhaka',
  225:	'Dr JS Moroka',
  226:	'Umvoti',
  227:	'Sundays River Valley',
  228:	'George',
  229:	'Greater Letaba',
  230:	'Mbhashe',
  231:	'Kannaland',
  232:	'Greater Giyani',
  233:	'South Cape',
  234:	'Breede Valley',
  235:	'Abaqulusi',
  236:	'Thembelihle',
  237:	'Prince Albert',
  238:	'Kamiesberg',
  239:	'Indaka',
  240:	'Cederberg',
  241:	'The Big 5 False Bay',
  242:	'Umzimkhulu',
  243:	'Umzumbe',
  244:	'Nkonkobe',
  245:	'Kwa Sani',
  246:	'Fetakgomo',
  247:	'Polokwane',
  248:	'Kalahari',
  249:	'Richtersveld',
  250:	'Mafube',
  251:	'Lukanji',
  252:	'Utrecht',
  253:	'Nyandeni',
  254:	'Greater Kokstad',
  255:	'Makana',
  256:	'Midvaal',
  257:	'Engcobo',
  258:	'Tsantsabane',
  259:	'Highlands',
  260:	'Kou-Kamma',
  261:	'Govan Mbeki',
  262:	'Mangaung',
  263:	'Ntambanana',
  264:	'Mkhomazi Wilderness Area',
  265:	'Kai !Garib',
  266:	'Jozini',
  267:	'Gariep',
  268:	'Thabazimbi',
  269:	'Setsoto',
  270:	'Nkandla',
  271:	'!Kheis',
  272:	'Matzikama',
  273:	'Benede Oranje',
  274:	'Umdoni',
  275:	'Nongoma',
  276:	'Umzimvubu',
  277:	'Ngwathe',
  278:	'Stellenbosch',
  279:	'Matatiele',
  280:	'Mhlontlo',
  281:	'Merafong City',
  282:	'Maruleng',
  283:	'Imbabazane',
  284:	'Nxuba',
  285:	'Theewaterskloof',
  286:	'Siyathemba',
  287:	'Tlokwe City Council',
  288:	'City of Tshwane',
  289:	'Emalahleni',
  290:	'Thaba Chweu',
  291:	'Breede Valley',
  292:	'Sol Plaatjie',
  293:	'Musina',
  294:	'uMlalazi',
  295:	'Ubuhlebezwe',
  296:	'Tsolwana',
  297:	'Breede Valley',
  298:	'Naledi',
  299:	'West Rand',
  300:	'Hantam',
  301:	'Richmond',
  302:	'Ga-Segonyana',
  303:	'eNdondakusuka',
  304:	'Nketoana',
  305:	'Mnquma',
  306:	'Port St Johns',
  307:	'Overstrand',
  308:	'uMuziwabantu',
  309:	'Makhuduthamaga',
  310:	'Great Kei',
  311:	'Kareeberg',
  312:	'Greater Tubatse',
  313:	'Ga-Segonyana',
  314:	'Ventersdorp',
  315:	'Mkhambathini',
  316:	'Joe Morolong',
  317:	'City of Matlosana',
  318:	'Modimolle',
  319:	'uMngeni',
  320:	'Kgatelopele',
  321:	'Umhlabuyalingana',
  322:	'Randfontein',
  323:	'Lepele-Nkumpi',
  324:	'Tswaing',
  325:	'Mkhondo',
  326:	'Mutale',
  327:	'Ephraim Mogale',
  328:	'Gamagara',
  329:	'Emfuleni',
  330:	'Mohokare',
  331:	'Ditsobotla',
  332:	'City of Tshwane',
  333:	'Tswelopele',
  334:	'Saldanha Bay',
  335:	'Mamusa',
  336:	'Mookgopong',
  337:	'Setla-Kgobi',
  338:	'Kagisano/Molopo',
  339:	'Dipaleseng',
  340:	'Beaufort West',
  341:	'Nala',
  342:	'Maquassi Hills',
  343:	'St Lucia Park',
  344:	'Mogale City',
  345:	'//Khara Hais',
  346:	'Ekurhuleni',
  347:	'Lesedi',
  348:	'Elias Motsoaledi',
  349:	'Kopanong',
  350:	'eDumbe',
  351:	'Nqutu',
  352:	'Mountain Zebra National Park',
  353:	'Oviston Nature Reserve',
  354:	'Golden Gate Highlands National Park',
  355:	'NULL',
  356:	'Highmoor/Kamberg Park',
  357:	'NULL',
  358:	'NULL',
  359:	'Pilansberg National Park',
  360:	'Overberg',
  361:	"O'Conners Camp",
  362:	'Schuinsdraai Nature Reserve',
  363:	'Mdala Nature Reserve',
};
// Total received data
var currentTotalData = [];
// Currency formatting function
Number.prototype.formatRands = function () {
  return customFormat.numberFormat("$,.6s")(this*1000);
}; //Attribution: http://stackoverflow.com/questions/149055/how-can-i-format-numbers-as-money-in-javascript?page=1&tab=votes#tab-top

// Percentage formatting function
Number.prototype.percentify = function(){
  return String((this*100).toFixed(1)) + "%";
}

//Check for already loaded large datasets
function checkDataCacheing(field, subfield){
  if (field == 'DwellingType') {
    if (TotalHousingTypeData.length == 0) {
      // Perform a standard lookup
      Websocket.emit('Municipal_Housing', subfield);
      genericDataSend('Census Dwelling type');
      animateLoad('Housing');
    } else {
      if (subfield == 'Informal') {
        var extractOptions = ['Municipality', 'HousingType', '', [7,8]];
        extractColorKeys(TotalHousingTypeData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Living in Informal Housing";
        legend.update('Municipal', colorScale);
      }//Informal
      if (subfield == 'Traditional') {
        var extractOptions = ['Municipality', 'HousingType', '', [2,15]];
        extractColorKeys(TotalHousingTypeData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Living in Traditional Housing";
        legend.update('Municipal', colorScale);
      }//Traditional
    }//else
  }//DwellingType
  if (field == 'Services') {
    if (TotalHousingServicesData.length == 0) {
      // Perform a standard lookup
      Websocket.emit('Municipal_Services', subfield);
      genericDataSend('Census Household services');
      animateLoad('Services');
    } else {
      if (subfield == 'Water') {
        var extractOptions = ['Municipality', 'HousingServices', 'WaterKey', [7,8,9]];
        extractColorKeys(TotalHousingServicesData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "No Water Access";
        legend.update('Municipal', colorScale);
      }//Water
      if (subfield == 'Electricity') {
        var extractOptions = ['Municipality', 'HousingServices', 'EnergyKey', [3,4,5,6,7,8]];
        extractColorKeys(TotalHousingServicesData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "No Electricity Access";
        legend.update('Municipal', colorScale);
      }//Electricity
      if (subfield == 'Telephone') {
        var extractOptions = ['Municipality', 'HousingServices', 'TelephoneKey', [4,6,7,8,10,11]];
        extractColorKeys(TotalHousingServicesData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "No Telephone Access";
        legend.update('Municipal', colorScale);
      }//Telephone
      if (subfield == 'Toilet') {
        var extractOptions = ['Municipality', 'HousingServices', 'ToiletKey', [4,5,6,7,8]];
        extractColorKeys(TotalHousingServicesData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "No Ablution Facilities";
        legend.update('Municipal', colorScale);
      }//Toilet
    }//else
  }//Services
  if (field == 'Mortality') {
    if (TotalMortalityData.length == 0) {
      Websocket.emit('Municipal_Mortality', subfield);
      genericDataSend('Census Mortality');
      animateLoad('Mortality');
    } else {
      if (subfield == 'Infant') {
        var extractOptions = ['Municipality', 'Mortality', '', [1,2]];
        extractColorKeys(TotalMortalityData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Infants without Parents";
        legend.update('Municipal', colorScale);
      }
      if (subfield == 'Youth') {
        var extractOptions = ['Municipality', 'Mortality', '', [3,4]];
        extractColorKeys(TotalMortalityData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Youth without Parents";
        legend.update('Municipal', colorScale);
      }
      if (subfield == 'Young Adult') {
        var extractOptions = ['Municipality', 'Mortality', '', [5,6,7,8]];
        extractColorKeys(TotalMortalityData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Young Adults without Parents";
        legend.update('Municipal', colorScale);
      }
    }//else
  }//Mortality
  if (field == 'Education') {
    if (TotalEducationData.length == 0) {
      Websocket.emit('Municipal_Education', subfield);
      genericDataSend('Census Education');
      animateLoad('Education');
    }else {
      if (subfield == 'None') {
        var extractOptions = ['Municipality', 'Education', '', [1]];
        extractColorKeys(TotalEducationData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Individuals with No Formal Schooling";
        legend.update('Municipal', colorScale);
      }//if none
      if (subfield == 'Grade 7') {
        var extractOptions = ['Municipality', 'Education', '', [9]];
        extractColorKeys(TotalEducationData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Highest qualification: Grade 7";
        legend.update('Municipal', colorScale);
      }//if Grade 7
      if (subfield == 'Matric') {
        var extractOptions = ['Municipality', 'Education', '', [16,17,18]];
        extractColorKeys(TotalEducationData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Highest qualification: Matric";
        legend.update('Municipal', colorScale);
      }//if Matric
      if (subfield == 'University') {
        var extractOptions = ['Municipality', 'Education', '', [19,20,21,22,23,24]];
        extractColorKeys(TotalEducationData, extractOptions);
        var colorScale = createColourScale(municipalColourKey);
        CreateMunicipalLayer();
        selectionType = "Highest qualification: Tertiary";
        legend.update('Municipal', colorScale);
      }//if University
    }//else
  }//Education
}//checkDataCacheing

//Aggregate a chosen data field
function simpleAggregateField(data, aggField, compareField, item){
  var total = 0;
  for (var i = 0; i < data.length; i++) {
    if (data[i][compareField] == item){
      total += data[i][aggField];
    }
  }
  return total;
}//simpleAggregateField

//More intensive Aggregation
function complexAggregateField(data, aggField, compareField1, compareField2, item1, item2){
  var total = 0;
  for (var i = 0; i < data.length; i++) {
    if(data[i][compareField1] == item1 && data[i][compareField2] == item2){
      total += data[i][aggField];
    }
  }
  return total;
}//complexAggregateField

//Extract Provincial color mapping
// Options structure :
// [LayerType, layerSubType, layer field, layerSubType keys]
function extractColorKeys(data, options){
  if (options[0] == 'Province'){
    if (options[1] == 'Total') {
      for (province in provinceColourKey){
        provinceColourKey[province] = simpleAggregateField(data, options[2], 'ProvinceKey', provinceKey[province]);
      }//for
    }
    if (options[1] == 'Department') {
      for (province in provinceColourKey){
        provinceColourKey[province] = complexAggregateField(data, options[2], 'ProvinceKey', 'DepartmentKey', provinceKey[province], options[3]);
      }//for
    }
  }//if
  if (options[0] == 'Municipality'){
    if (options[1] == 'HousingType') {
      calculateHousingTypeScore(data, options[3]);
    }// if housingType
    if (options[1] == 'HousingServices') {
      calculateHousingServicesScore(data, options[2], options[3]);
    }// if housing services
    if (options[1] == 'Mortality') {
      calculateMortalityScore(data, options[3]);
    }// if mortality
    if (options[1] == 'Education') {
      calculateEducationScore(data, options[3]);
    }
  }// if Municipality
}//extractColorKeys

// Calculation of Housing Dwelling-type scores
function calculateHousingTypeScore(housingTypeData, serviceKeys){
  // Reset municipalColourKey for plotting
  for (municipality in tempMunicContainer){
    tempMunicContainer[municipality] = [0,0];
  }//for
  // Add up housing totals per municipality
  for (var i = 0; i < housingTypeData.length; i++) {
    if (tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]] != undefined) {
      if (serviceKeys.indexOf(housingTypeData[i]['DwellingTypeKey']) > -1){
        tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]][0] = tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]][0] + housingTypeData[i]['Amount'];
        tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]][1] + housingTypeData[i]['Amount'];
      }//if housingTypeData
      else {
        tempMunicContainer[keyToMunicipality[housingTypeData[i]['MunicipalityKey']]][1] += housingTypeData[i]['Amount'];
      }//else
    }//if != undefined
  }//for
  //Average all values
  for (municipality in municipalColourKey){
    municipalColourKey[municipality] = tempMunicContainer[municipality][0]/tempMunicContainer[municipality][1];
    if (municipalColourKey[municipality] == NaN) {
      municipalColourKey[municipality] = 0;
    }
  }//for
}//calculateHousingDataScore

// Calculation of Housing Service scores
function calculateHousingServicesScore(housingServiceData, serviceField, serviceKeys){
  //Reset municipalColourKey for plotting
  for (var municipality in tempMunicContainer) {
    tempMunicContainer[municipality] = [0,0];
  }// for
  //Perform aggregation of various Household services
  for (var i = 0; i < housingServiceData.length; i++) {
    if (tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]] != undefined) {
      // Determine if given key matches service field
      if (serviceKeys.indexOf(housingServiceData[i][serviceField]) > -1) {
        tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]][0] = tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]][0] + housingServiceData[i]['Amount'];
        tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]][1] + housingServiceData[i]['Amount'];
      } else {
        tempMunicContainer[keyToMunicipality[housingServiceData[i]['MunicipalityKey']]][1] += housingServiceData[i]['Amount'];
      }// else
    }// if tempMunicContainer != undefined
  }// for housingServiceData
  //Average all values
  for (municipality in municipalColourKey){
    municipalColourKey[municipality] = tempMunicContainer[municipality][0]/tempMunicContainer[municipality][1];
    if (municipalColourKey[municipality] == NaN) {
      municipalColourKey[municipality] = 0;
    }// if == NaN
  }//for municipality
}// housingServiceData

// Calculation of Mortality Rate scores
function calculateMortalityScore(mortalityData, serviceKeys){
  //Reset municipalColourKey for plotting
  for (var municipality in tempMunicContainer) {
    tempMunicContainer[municipality] = [0,0];
  }// for
  // Perform aggregation of deaths for ageGroups
  for (var i = 0; i < mortalityData.length; i++) {
    if (tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]] != undefined) {
      // Determine if data is in correct mortality Category
      if (serviceKeys.indexOf(mortalityData[i]['AgeGroupKey']) > -1 && mortalityData[i]['MotherAliveKey'] == 2 && mortalityData[i]['FatherAliveKey'] == 2) {
        tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][0] = tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][0] + mortalityData[i]['Amount'];
        tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][1] + mortalityData[i]['Amount'];
      }else {
        tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[mortalityData[i]['MunicipalityKey']]][1] + mortalityData[i]['Amount'];
      }//else
    }// if undefined
  }// for mortalityData
  //Average all values
  for (municipality in municipalColourKey){
    municipalColourKey[municipality] = tempMunicContainer[municipality][0]/tempMunicContainer[municipality][1];
    if (municipalColourKey[municipality] == NaN) {
      municipalColourKey[municipality] = 0;
    }// if == NaN
  }//for municipality
}// calculateMortalityScore

// Calculation of Highest Education level scores
function calculateEducationScore(educationData, serviceKeys){
  //Reset municipalColourKey for plotting
  for (var municipality in tempMunicContainer) {
    tempMunicContainer[municipality] = [0,0];
  }// for
  for (var i = 0; i < educationData.length; i++) {
    if (tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]] != undefined) {
      // Determine if data is in correct mortality Category
      if (serviceKeys.indexOf(educationData[i]['HighestEducationLevelKey']) > -1) {
        tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][0] = tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][0] + educationData[i]['Amount'];
        tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][1] + educationData[i]['Amount'];
      }else {
        tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][1] = tempMunicContainer[keyToMunicipality[educationData[i]['MunicipalityKey']]][1] + educationData[i]['Amount'];
      }//else
    }// if undefined
  }// for educationData
  //Average all values
  for (municipality in municipalColourKey){
    municipalColourKey[municipality] = tempMunicContainer[municipality][0]/tempMunicContainer[municipality][1];
    if (municipalColourKey[municipality] == NaN) {
      municipalColourKey[municipality] = 0;
    }// if == NaN
  }//for municipality
}// calculateEducationScore
