// Yalnız okumalar için kapasite sınırı. Yazma/kabul kapıları bu kuyruğa girmez.
export class ReadSchedule {
 constructor(limit=2){this.limit=limit;this.active=0;this.waiting=[];}
 run(operation){return new Promise((resolve,reject)=>{this.waiting.push({operation,resolve,reject});this.drain();});}
 drain(){while(this.active<this.limit&&this.waiting.length){
  const item=this.waiting.shift();this.active++;
  Promise.resolve().then(item.operation).then(item.resolve,item.reject).finally(()=>{this.active--;this.drain();});
 }}
}

// Devam eden yenileme sırasında gelen çağrılar, onu izleyen tek taze okumada birleşir.
// Böylece bir iş kabulünden sonra istenen yenileme eski okumayla karşılanmaz.
export class RefreshSchedule {
 constructor(){this.running=false;this.next=null;}
 run(operation){return new Promise((resolve,reject)=>{
  if(this.running){this.next??={operation,waiters:[]};this.next.operation=operation;this.next.waiters.push({resolve,reject});}
  else{this.running=true;void this.execute({operation,waiters:[{resolve,reject}]});}
 });}
 async execute(group){
  try{const value=await group.operation();for(const waiter of group.waiters)waiter.resolve(value);}
  catch(error){for(const waiter of group.waiters)waiter.reject(error);}
  finally{const next=this.next;this.next=null;if(next)void this.execute(next);else this.running=false;}
 }
}
