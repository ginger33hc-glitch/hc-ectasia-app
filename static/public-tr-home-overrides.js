/* Turkish homepage overrides for founder note and approved Turkish product name. */
(() => {
  const TURKISH_NAME = "Kornel Ektazi Riski Değerlendirmesinde Yapay Zeka";
  const founderHtmlTr = [
    "Otuz yılı aşkın cerrahi ve idari deneyimden sonra, biriktirdiğim bilgi ve deneyimin bir bölümünü benden sonraki kuşaklara aktarabilmenin bir yolunu bulmak istedim.",
    "Bir refraktif cerrah olarak en çok çekindiğimiz komplikasyonlardan biri korneal ektazidir. Amacım, cerrahi öncesinde ektazi yatkınlığını daha güvenilir biçimde belirlemeye yardımcı olabilecek ve sonuçta hastaları önlenebilir bir komplikasyondan korumaya katkı sağlayabilecek bir sistem geliştirmekti. Yapay zekânın hızlı gelişimiyle birlikte, yerleşik klinik kanıtları, modern görüntüleme verilerini ve kendi cerrahi deneyimimi yapılandırılmış bir klinik karar destek platformunda birleştirmeye karar verdim.",
    "Proje ilk olarak <strong>HC-Ectasia-App</strong> adıyla başladı. Daha sonra <strong>CERAI — Corneal Ectasia Risk Analysis Intelligence</strong> biçimine evrildi ve sonunda <strong>CER-AI — Kornel Ektazi Riski Değerlendirmesinde Yapay Zeka</strong> adını aldı.",
    "Yazılım 0.1, 0.2, 0.3 sürümleri ve sonraki geliştirmelerle aşamalı olarak ilerledi; bu metnin yazıldığı sırada <strong>0.7.71</strong> sürümüne ulaştı. Geliştirme sürekli devam ettiği için siz bunu okurken daha yeni bir sürüm kullanımda olabilir.",
    "Geliştirme sürecinde korneal ektazi, keratokonus yatkınlığı, refraktif cerrahi taraması, kornea tomografisi, topografi, biyomekanik ve doku güvenliğiyle ilgili tıbbi literatürü kapsamlı biçimde gözden geçirdim. Bu kanıtları pratik cerrahi deneyimle birleştirerek farklı ektazi risk değerlendirme sistemlerini tek bir çerçeve içinde bir araya getirdim.",
    "CER-AI'nin temel ilkelerinden biri, bu sistemlerin <strong>birbirinden bağımsız kalmasıdır</strong>. Bunları tek ve şeffaf olmayan bir puanda birleştirmek yerine, her değerlendirme yolu vakayı ayrı olarak inceler; böylece cerrah farklı risk değerlendirme yaklaşımlarının nerede uyumlu, nerede farklı sonuç verdiğini görebilir.",
    "CER-AI'nin temel amacı hekimin yerine cerrahi karar vermek değildir. Sistem; <strong>hekimin karar verme sürecini desteklemek</strong>, karmaşık preoperatif bilgiyi düzenlemek ve en önemlisi gözden kaçabilecek bir bulgunun fark edilmesine yardımcı olmak üzere tasarlanmıştır.",
    "Özellikle genç meslektaşlarıma, cerrahi kariyerim boyunca bana yol gösteren şu ilkeyi vurgulamak isterim: <strong>Hangi işlemi yaparsak yapalım, ilk sorumluluğumuz hastaya zarar vermemektir.</strong>",
    "Teknoloji, görüntüleme, puanlama sistemleri ve yapay zekâ bize yardımcı olabilir; ancak bunların tümü her zaman bu temel klinik sorumluluğa hizmet etmelidir."
  ];

  const originals = new WeakMap();
  function remember(el) {
    if (el && !originals.has(el)) originals.set(el, el.innerHTML);
  }

  function apply() {
    const tr = document.documentElement.lang === "tr";
    document.querySelectorAll(".subtitle").forEach(el => {
      remember(el);
      el.textContent = tr ? TURKISH_NAME : el.textContent;
      if (!tr) el.innerHTML = originals.get(el);
    });
    const brand = document.querySelector(".brand-subtitle");
    if (brand) {
      remember(brand);
      if (tr) brand.textContent = TURKISH_NAME;
      else brand.innerHTML = originals.get(brand);
    }
    document.querySelectorAll("footer strong").forEach(el => {
      remember(el);
      if (tr && el.textContent.includes("CER-AI")) el.textContent = `CER-AI — ${TURKISH_NAME}`;
      else if (!tr) el.innerHTML = originals.get(el);
    });

    const note = document.querySelector(".founder-note");
    if (!note) return;
    const heading = note.querySelector("h2");
    if (heading) heading.textContent = tr ? "Kurucunun Notu" : "Founder’s Note";
    const paras = [...note.querySelectorAll("p")];
    paras.forEach((p, i) => {
      remember(p);
      if (tr && founderHtmlTr[i]) p.innerHTML = founderHtmlTr[i];
      else if (!tr) p.innerHTML = originals.get(p);
    });
  }

  function init() {
    apply();
    new MutationObserver(mutations => {
      if (mutations.some(m => m.type === "attributes" && m.attributeName === "lang")) apply();
    }).observe(document.documentElement, {attributes:true, attributeFilter:["lang"]});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once:true});
  else init();
})();
